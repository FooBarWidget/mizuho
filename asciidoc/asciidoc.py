#!/usr/bin/env python
"""
asciidoc - converts an AsciiDoc text file to DocBook, HTML or LinuxDoc

Copyright (C) 2002-2008 Stuart Rackham. Free use of this software is granted
under the terms of the GNU General Public License (GPL).
"""

import sys, os, re, time, traceback, tempfile, popen2, codecs, locale
from types import *

VERSION = '8.2.7'   # See CHANGLOG file for version history.

#---------------------------------------------------------------------------
# Program onstants.
#---------------------------------------------------------------------------
DEFAULT_BACKEND = 'xhtml11'
DEFAULT_DOCTYPE = 'article'
# Allowed substitution options for List, Paragraph and DelimitedBlock
# definition subs entry.
SUBS_OPTIONS = ('specialcharacters','quotes','specialwords',
    'replacements', 'attributes','macros','callouts','normal','verbatim',
    'none','passthroughs','replacements2')
# Default value for unspecified subs and presubs configuration file entries.
SUBS_NORMAL = ('specialcharacters','quotes','attributes',
    'specialwords','replacements','macros','passthroughs')
SUBS_VERBATIM = ('specialcharacters','callouts')

NAME_RE = r'(?u)[^\W\d][-\w]*'  # Valid section or attrbibute name.


#---------------------------------------------------------------------------
# Utility functions and classes.
#---------------------------------------------------------------------------

class EAsciiDoc(Exception):
    pass


from UserDict import UserDict

class OrderedDict(UserDict):
    """
    Dictionary ordered by insertion order.
    Python Cookbook: Ordered Dictionary, Submitter: David Benjamin.
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/107747
    """
    def __init__(self, d=None):
        self._keys = []
        UserDict.__init__(self, d)
    def __delitem__(self, key):
        UserDict.__delitem__(self, key)
        self._keys.remove(key)
    def __setitem__(self, key, item):
        UserDict.__setitem__(self, key, item)
        if key not in self._keys: self._keys.append(key)
    def clear(self):
        UserDict.clear(self)
        self._keys = []
    def copy(self):
        d = UserDict.copy(self)
        d._keys = self._keys[:]
        return d
    def items(self):
        return zip(self._keys, self.values())
    def keys(self):
        return self._keys
    def popitem(self):
        try:
            key = self._keys[-1]
        except IndexError:
            raise KeyError('dictionary is empty')
        val = self[key]
        del self[key]
        return (key, val)
    def setdefault(self, key, failobj = None):
        UserDict.setdefault(self, key, failobj)
        if key not in self._keys: self._keys.append(key)
    def update(self, d=None, **kwargs):
        if d is None:
            d = kwargs
        UserDict.update(self, d)
        for key in d.keys():
            if key not in self._keys: self._keys.append(key)
    def values(self):
        return map(self.get, self._keys)

def print_stderr(line):
    sys.stderr.write(line+os.linesep)

def verbose(msg,linenos=True):
    if config.verbose:
        console(msg,linenos=linenos)

def warning(msg,linenos=True):
    console(msg,'WARNING: ',linenos)
    document.has_warnings = True

def deprecated(old, new, linenos=True):
    console('%s: %s' % (old,new), 'DEPRECATED: ', linenos)

def error(msg, cursor=None):
    """Report fatal error but don't exit application, continue in the hope of
    reporting all fatal errors finishing with a non-zero exit code."""
    console(msg,'ERROR: ', cursor=cursor)
    document.has_errors = True

def console(msg, prefix='', linenos=True, cursor=None):
    """Print message to stderr. 'offset' is added to reported line number for
    warnings emitted when reading ahead."""
    s = prefix
    if linenos and reader.cursor:
        if not cursor:
            cursor = reader.cursor
        s = s + '%s: line %d: ' % (os.path.basename(cursor[0]),cursor[1])
    s = s + msg
    print_stderr(s)

def file_in(fname, directory):
    """Return True if file fname resides inside directory."""
    assert os.path.isfile(fname)
    # Empty directory (not to be confused with None) is the current directory.
    if directory == '':
        directory = os.getcwd()
    else:
        assert os.path.isdir(directory)
        directory = os.path.abspath(directory)
    fname = os.path.realpath(fname)
    return os.path.commonprefix((directory, fname)) == directory

def safe():
    return document.safe

def is_safe_file(fname, directory=None):
    # A safe file must reside in directory directory (defaults to the source
    # file directory).
    if directory is None:
        if document.infile == '<stdin>':
           return not safe()
        directory = os.path.dirname(document.infile)
    elif directory == '':
        directory = '.'
    return not safe() or file_in(fname, directory)

# Return file name which must reside in the parent file directory.
# Return None if file is not found or not safe.
def safe_filename(fname, parentdir):
    if not os.path.isabs(fname):
        # Include files are relative to parent document
        # directory.
        fname = os.path.join(parentdir,fname)
    if not os.path.isfile(fname):
        warning('include file not found: %s' % fname)
        return None
    if not is_safe_file(fname, parentdir):
        unsafe_error('include file: %s' % fname)
        return None
    return fname

def unsafe_error(msg):
    error('unsafe: '+msg)

def syseval(cmd):
    # Run shell command and return stdout.
    child = os.popen(cmd)
    data = child.read()
    err = child.close()
    if not err:
        return data
    else:
        return ''

def assign(dst,src):
    """Assign all attributes from 'src' object to 'dst' object."""
    for a,v in src.__dict__.items():
        setattr(dst,a,v)

def strip_quotes(s):
    """Trim white space and, if necessary, quote characters from s."""
    s = s.strip()
    # Strip quotation mark characters from quoted strings.
    if len(s) >= 3 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    return s

def is_regexp(s):
    """Return True if s is a valid regular expression else return False."""
    try: re.compile(s)
    except: return False
    else: return True

def join_regexp(relist):
    """Join list of regular expressions re1,re2,... to single regular
    expression (re1)|(re2)|..."""
    if len(relist) == 0:
        return None
    result = []
    # Delete named groups to avoid ambiguity.
    for s in relist:
        result.append(re.sub(r'\?P<\S+?>','',s))
    result = ')|('.join(result)
    result = '('+result+')'
    return result

def validate(value,rule,errmsg):
    """Validate value against rule expression. Throw EAsciiDoc exception with
    errmsg if validation fails."""
    try:
        if not eval(rule.replace('$',str(value))):
            raise EAsciiDoc,errmsg
    except:
        raise EAsciiDoc,errmsg
    return value

def join_lines(lines):
    """Return a list in which lines terminated with the backslash line
    continuation character are joined."""
    result = []
    s = ''
    continuation = False
    for line in lines:
        if line and line[-1] == '\\':
            s = s + line[:-1]
            continuation = True
            continue
        if continuation:
            result.append(s+line)
            s = ''
            continuation = False
        else:
            result.append(line)
    if continuation:
        result.append(s)
    return result

def dovetail(lines1, lines2):
    """Append list or tuple of strings 'lines2' to list 'lines1'.  Join the
    last string in 'lines1' with the first string in 'lines2' into a single
    string."""
    assert isinstance(lines1,list) or isinstance(lines1,tuple)
    assert isinstance(lines2,list) or isinstance(lines2,tuple)
    if not lines1 or not lines2:
        return list(lines1) + list(lines2)
    result = list(lines1[:-1])
    result.append(lines1[-1] + lines2[0])
    result += list(lines2[1:])
    return result

def dovetail_tags(stag,content,etag):
    """Merge the end tag with the first content line and the last
    content line with the end tag. This ensures verbatim elements don't
    include extraneous opening and closing line breaks."""
    return dovetail(dovetail(stag,content), etag)

def parse_attributes(attrs,dict):
    """Update a dictionary with name/value attributes from the attrs string.
    The attrs string is a comma separated list of values and keyword name=value
    pairs. Values must preceed keywords and are named '1','2'... The entire
    attributes list is named '0'. If keywords are specified string values must
    be quoted. Examples:

    attrs: ''
    dict: {}

    attrs: 'hello,world'
    dict: {'2': 'world', '0': 'hello,world', '1': 'hello'}

    attrs: '"hello", planet="earth"'
    dict: {'planet': 'earth', '0': '"hello",planet="earth"', '1': 'hello'}
    """
    def f(*args,**keywords):
        # Name and add aguments '1','2'... to keywords.
        for i in range(len(args)):
            if not keywords.has_key(str(i+1)):
                keywords[str(i+1)] = args[i]
        return keywords

    if not attrs:
        return
    dict['0'] = attrs
    # Replace line separators with spaces so line spanning works.
    s = re.sub(r'\s', ' ', attrs)
    try:
        d = eval('f('+s+')')
        # Attributes must evaluate to strings, numbers or None.
        for v in d.values():
            if not (isinstance(v,str) or isinstance(v,int) or isinstance(v,float) or v is None):
                raise
        dict.update(d)
    except:
        # Try quoting the attrs.
        s = s.replace('"',r'\"') # Escape double-quotes.
        s = s.split(',')
        s = map(lambda x: '"' + x.strip() + '"', s)
        s = ','.join(s)
        try:
            d = eval('f('+s+')')
        except:
            return  # If there's a syntax error leave with {0}=attrs.
        for k in d.keys():  # Drop any empty positional arguments.
            if d[k] == '': del d[k]
        dict.update(d)
    assert len(d) > 0

def parse_named_attributes(s,attrs):
    """Update a attrs dictionary with name="value" attributes from the s string.
    Returns False if invalid syntax.
    Example:
    attrs: 'star="sun",planet="earth"'
    dict: {'planet':'earth', 'star':'sun'}
    """
    def f(**keywords): return keywords

    try:
        d = eval('f('+s+')')
        attrs.update(d)
        return True
    except:
        return False

def parse_list(s):
    """Parse comma separated string of Python literals. Return a tuple of of
    parsed values."""
    try:
        result = eval('tuple(['+s+'])')
    except:
        raise EAsciiDoc,'malformed list: '+s
    return result

def parse_options(options,allowed,errmsg):
    """Parse comma separated string of unquoted option names and return as a
    tuple of valid options. 'allowed' is a list of allowed option values.
    If allowed=() then all legitimate names are allowed.
    'errmsg' is an error message prefix if an illegal option error is thrown."""
    result = []
    if options:
        for s in re.split(r'\s*,\s*',options):
            if (allowed and s not in allowed) or (s == '' or not is_name(s)):
                raise EAsciiDoc,'%s: %s' % (errmsg,s)
            result.append(s)
    return tuple(result)

def symbolize(s):
    """Drop non-symbol characters and convert to lowercase."""
    return re.sub(r'(?u)[^\w\-_]', '', s).lower()

def is_name(s):
    """Return True if s is valid attribute, macro or tag name
    (starts with alpha containing alphanumeric and dashes only)."""
    return re.match(NAME_RE,s) is not None

def subs_quotes(text):
    """Quoted text is marked up and the resulting text is
    returned."""
    # The quote patterns are iterated in reverse sort order to avoid ambiguity.
    # So, for example, __ is processed before _.
    keys = config.quotes.keys()
    keys.sort()
    keys.reverse()
    for q in keys:
        i = q.find('|')
        if i != -1 and q != '|' and q != '||':
            lq = q[:i]      # Left quote.
            rq = q[i+1:]    # Right quote.
        else:
            lq = rq = q
        tag = config.quotes[q]
        # Unconstrained quotes prefix the tag name with a hash.
        if tag[0] == '#':
            tag = tag[1:]
            # Unconstrained quotes can appear anywhere.
            reo = re.compile(r'(?msu)(^|.)(\[(?P<attrs>[^[]+?)\])?' \
                    + r'(?:' + re.escape(lq) + r')' \
                    + r'(?P<content>.+?)(?:'+re.escape(rq)+r')')
        else:
            # The text within constrained quotes must be bounded by white space.
            # Non-word (\W) characters are allowed at boundaries to accomodate
            # enveloping quotes.
            reo = re.compile(r'(?msu)(^|\W)(\[(?P<attrs>[^[]+?)\])?' \
                + r'(?:' + re.escape(lq) + r')' \
                + r'(?P<content>.+?)(?:'+re.escape(rq)+r')(?=\W|$)')
        pos = 0
        while True:
            mo = reo.search(text,pos)
            if not mo: break
            if text[mo.start()] == '\\':
                pos = mo.end()
            else:
                attrs = {}
                parse_attributes(mo.group('attrs'), attrs)
                stag,etag = config.tag(tag, attrs)
                s = mo.group(1) + stag + mo.group('content') + etag
                text = text[:mo.start()] + s + text[mo.end():]
                pos = mo.start() + len(s)
        # Unescape escaped quotes.
        text = text.replace('\\'+lq, lq)
        if lq != rq:
            text = text.replace('\\'+rq, rq)
    return text

def subs_tag(tag,dict={}):
    """Perform attribute substitution and split tag string returning start, end
    tag tuple (c.f. Config.tag())."""
    s = subs_attrs(tag,dict)
    if not s:
        warning('tag "%s" dropped: contains undefined attribute' % tag)
        return [None,None]
    result = s.split('|')
    if len(result) == 1:
        return result+[None]
    elif len(result) == 2:
        return result
    else:
        raise EAsciiDoc,'malformed tag: %s' % tag

def parse_entry(entry, dict=None, unquote=False, unique_values=False,
        allow_name_only=False, escape_delimiter=True):
    """Parse name=value entry to dictionary 'dict'. Return tuple (name,value)
    or None if illegal entry.
    If name= then value is set to ''.
    If name and allow_name_only=True then value is set to ''.
    If name! and allow_name_only=True then value is set to None.
    Leading and trailing white space is striped from 'name' and 'value'.
    'name' can contain any printable characters.
    If the '=' delimiter character is allowed in  the 'name' then 
    it must be escaped with a backslash and escape_delimiter must be True.
    If 'unquote' is True leading and trailing double-quotes are stripped from
    'name' and 'value'.
    If unique_values' is True then dictionary entries with the same value are
    removed before the parsed entry is added."""
    if escape_delimiter:
        mo = re.search(r'(?:[^\\](=))',entry)
    else:
        mo = re.search(r'(=)',entry)
    if mo:  # name=value entry.
        if mo.group(1):
            name = entry[:mo.start(1)]
            if escape_delimiter:
                name = name.replace(r'\=','=')  # Unescape \= in name.
            value = entry[mo.end(1):]
    elif allow_name_only and entry:         # name or name! entry.
        name = entry
        if name[-1] == '!':
            name = name[:-1]
            value = None
        else:
            value = ''
    else:
        return None
    if unquote:
        name = strip_quotes(name)
        if value is not None:
            value = strip_quotes(value)
    else:
        name = name.strip()
        if value is not None:
            value = value.strip()
    if not name:
        return None
    if dict is not None:
        if unique_values:
            for k,v in dict.items():
                if v == value: del dict[k]
        dict[name] = value
    return name,value

def parse_entries(entries, dict, unquote=False, unique_values=False,
        allow_name_only=False,escape_delimiter=True):
    """Parse name=value entries from  from lines of text in 'entries' into
    dictionary 'dict'. Blank lines are skipped."""
    for entry in entries:
        if entry and not parse_entry(entry, dict, unquote, unique_values,
                allow_name_only, escape_delimiter):
            raise EAsciiDoc,'malformed section entry: %s' % entry

def load_sections(sections, fname, dir=None, namepat=NAME_RE):
    """Loads sections dictionary with sections from file fname.
    Existing sections are overlaid. Silently skips missing configuration
    files."""
    if dir:
        fname = os.path.join(dir, fname)
    # Sliently skip missing configuration file.
    if not os.path.isfile(fname):
        return
    reo = re.compile(r'^\[(?P<section>'+namepat+')\]\s*$')
    section,contents = '',[]
    for line in open(fname):
        if line and line[0] == '#': # Skip comment lines.
            continue
        line = line.rstrip()
        found = reo.findall(line)
        if found:
            if section:             # Store previous section.
                sections[section] = contents
            section = found[0].lower()
            contents = []
        else:
            contents.append(line)
    if section and contents:        # Store last section.
        sections[section] = contents

def dump_section(name,dict,f=sys.stdout):
    """Write parameters in 'dict' as in configuration file section format with
    section 'name'."""
    f.write('[%s]%s' % (name,writer.newline))
    for k,v in dict.items():
        k = str(k)
        k = k.replace('=',r'\=')    # Escape = in name.
        # Quote if necessary.
        if len(k) != len(k.strip()):
            k = '"'+k+'"'
        if v and len(v) != len(v.strip()):
            v = '"'+v+'"'
        if v is None:
            # Don't dump undefined attributes.
            continue
        else:
            s = k+'='+v
        if s[0] == '#':
            s = '\\' + s    # Escape so not treated as comment lines.
        f.write('%s%s' % (s,writer.newline))
    f.write(writer.newline)

def update_attrs(attrs,dict):
    """Update 'attrs' dictionary with parsed attributes in dictionary 'dict'."""
    for k,v in dict.items():
        if not is_name(k):
            raise EAsciiDoc,'illegal attribute name: %s' % k
        attrs[k] = v

def filter_lines(filter_cmd, lines, dict={}):
    """
    Run 'lines' through the 'filter_cmd' shell command and return the result.
    The 'dict' dictionary contains additional filter attributes.
    """
    # BUG: Has problems finding filters with spaces in command name.
    if not filter_cmd:
        return lines
    # Perform attributes substitution on the filter command.
    s = subs_attrs(filter_cmd, dict)
    if not s:
        raise EAsciiDoc,'missing filter attribute: %s' % filter_cmd
    filter_cmd = s
    # Search for the filter command in  both user and application 'filters'
    # sub-directories.
    mo = re.match(r'^(?P<cmd>\S+)(?P<tail>.*)$', filter_cmd)
    cmd = mo.group('cmd')
    found = False
    if not os.path.dirname(cmd):
        # Check in asciidoc user and application directories for unqualified
        # file name.
        if USER_DIR:
            cmd2 = os.path.join(USER_DIR,'filters',cmd)
            if os.path.isfile(cmd2):
                found = True
        if not found:
            cmd2 = os.path.join(CONF_DIR,'filters',cmd)
            if os.path.isfile(cmd2):
                found = True
        if not found:
            cmd2 = os.path.join(APP_DIR,'filters',cmd)
            if os.path.isfile(cmd2):
                found = True
        if found:
            cmd = cmd2
    else:
        if os.__dict__.has_key('uname') and os.uname()[0][:6] == 'CYGWIN':
            # popen2() does not like non-drive letter path names under
            # Cygwin.
            s = syseval('cygpath -m ' + cmd).strip()
            if s:
                cmd = s
        if os.path.isfile(cmd):
            found = True
        else:
            warning('filter not found: %s' % cmd)
    if found:
        filter_cmd = '"' + cmd + '"' + mo.group('tail')
    verbose('filtering: ' + filter_cmd)
    if sys.platform == 'win32':
        # Paul Melis's <p.e.c.melis@rug.nl> patch for filters on Win32
        # This workaround is necessary because Windows select() doesn't
        # work with regular files.
        fd,tmp = tempfile.mkstemp()
        os.close(fd)
        try:
            try:
                # Windows doesn't like running scripts directly so explicitly
                # specify interpreter.
                if found:
                    if cmd[-3:] == '.py':
                        filter_cmd = 'python ' + filter_cmd
                    elif cmd[-3:] == '.rb':
                        filter_cmd = 'ruby ' + filter_cmd
                w = os.popen(filter_cmd + ' > "%s"' % tmp, 'w')
                i = 0
                while i < len(lines):
                    line = lines[i]
                    w.write(line + os.linesep)
                    i = i + 1
                w.close()
                result = []
                for s in open(tmp, 'rt'):
                    result.append(s.rstrip())
            except:
                raise EAsciiDoc,'filter error: %s' % filter_cmd
        finally:
            os.unlink(tmp)
    else:
        try:
            import select
            result = []
            r,w = popen2.popen2(filter_cmd)
            # Polled I/O loop to alleviate full buffer deadlocks.
            i = 0
            while i < len(lines):
                line = lines[i]
                if select.select([],[w.fileno()],[],0)[1]:
                    w.write(line+os.linesep)    # Use platform line terminator.
                    i = i+1
                if select.select([r.fileno()],[],[],0)[0]:
                    s = r.readline()
                    if not s: break             # Exit if filter output closes.
                    result.append(s.rstrip())
            w.close()
            for s in r:
                result.append(s.rstrip())
            r.close()
        except:
            raise EAsciiDoc,'filter error: %s' % filter_cmd
    # There's no easy way to guage whether popen2() found and executed the
    # filter, so guess that if it produced no output there is probably a
    # problem.
    if lines and not result:
        warning('no output from filter: %s' % filter_cmd)
    return result

def system(name, args, is_macro=False):
    """Evaluate a system attribute ({name:args}) or system block macro
    (name::[args]). If is_macro is True then we are processing a system
    block macro otherwise it's a system attribute.
    NOTE: The include1 attribute is used internally by the include1::[] macro
    and is not for public use."""
    if is_macro:
        syntax = '%s::[%s]'
        separator = '\n'
    else:
        syntax = '{%s:%s}'
        separator = writer.newline
    if name not in ('eval','sys','sys2','include','include1'):
        msg = 'illegal '+syntax % (name,args)
        if is_macro:
            msg += ': macro name'
        else:
            msg += ': executable attribute name'
        warning(msg)
        return None
    if name != 'include1':
        verbose(('evaluating: '+syntax) % (name,args))
    if safe() and name not in ('include','include1'):
        unsafe_error(syntax % (name,args))
        return None
    result = None
    if name == 'eval':
        try:
            result = eval(args)
            if result is True:
                result = ''
            elif result is False:
                result = None
            elif result is not None:
                result = str(result)
        except:
            warning((syntax+': expression evaluation error') % (name,args))
    elif name in ('sys','sys2'):
        result = ''
        fd,tmp = tempfile.mkstemp()
        os.close(fd)
        try:
            cmd = args
            cmd = cmd + (' > %s' % tmp)
            if name == 'sys2':
                cmd = cmd + ' 2>&1'
            if os.system(cmd):
                warning((syntax+': non-zero exit status') % (name,args))
            try:
                if os.path.isfile(tmp):
                    lines = [s.rstrip() for s in open(tmp)]
                else:
                    lines = []
            except:
                raise EAsciiDoc,(syntax+': temp file read error') % (name,args)
            result = separator.join(lines)
        finally:
            if os.path.isfile(tmp):
                os.remove(tmp)
    elif name == 'include':
        if not os.path.exists(args):
            warning((syntax+': file does not exist') % (name,args))
        elif not is_safe_file(args):
            unsafe_error(syntax % (name,args))
        else:
            result = [s.rstrip() for s in open(args)]
            if result:
                result = subs_attrs(result)
                result = separator.join(result)
                result = result.expandtabs(reader.tabsize)
            else:
                result = ''
    elif name == 'include1':
        result = separator.join(config.include1[args])
    else:
        assert False
    return result

def subs_attrs(lines, dictionary=None):
    """Substitute 'lines' of text with attributes from the global
    document.attributes dictionary and from t'dictionary' ('dictionary'
    entries take precedence). Return a tuple of the substituted lines.  'lines'
    containing undefined attributes are deleted. If 'lines' is a string then
    return a string.

    - Attribute references are substituted in the following order: simple,
      conditional, system.
    - Attribute references inside 'dictionary' entry values are substituted.
    """

    def end_brace(text,start):
        """Return index following end brace that matches brace at start in
        text."""
        assert text[start] == '{'
        n = 0
        result = start
        for c in text[start:]:
            # Skip braces that are followed by a backslash.
            if result == len(text)-1 or text[result+1] != '\\':
                if c == '{': n = n + 1
                elif c == '}': n = n - 1
            result = result + 1
            if n == 0: break
        return result

    if isinstance(lines,StringType):
        string_result = True
        lines = [lines]
    else:
        string_result = False
        lines = list(lines)
    if dictionary is None:
        attrs = document.attributes
    else:
        # Remove numbered document attributes so they don't clash with
        # attribute list positional attributes.
        attrs = {}
        for k,v in document.attributes.items():
            if not re.match(r'^\d+$', k):
                attrs[k] = v
        # Substitute attribute references inside dictionary values.
        dictionary = dictionary.copy()
        for k,v in dictionary.items():
            if v is None:
                del dictionary[k]
            else:
                v = subs_attrs(str(v))
                if v is None:
                    del dictionary[k]
                else:
                    dictionary[k] = v
        attrs.update(dictionary)
    # Substitute all attributes in all lines.
    for i in range(len(lines)-1,-1,-1): # Reverse iterate lines.
        text = lines[i]
        # Make it easier for regular expressions.
        text = text.replace('\\{','{\\')
        text = text.replace('\\}','}\\')
        # Expand simple attributes ({name}).
        # Nested attributes not allowed.
        reo = re.compile(r'(?su)\{(?P<name>[^\\\W][-\w]*?)\}(?!\\)')
        pos = 0
        while True:
            mo = reo.search(text,pos)
            if not mo: break
            s =  attrs.get(mo.group('name'))
            if s is None:
                pos = mo.end()
            else:
                s = str(s)
                text = text[:mo.start()] + s + text[mo.end():]
                pos = mo.start() + len(s)
        # Expand conditional attributes.
        reo = re.compile(r'(?su)\{(?P<name>[^\\\W][-\w]*?)' \
                         r'(?P<op>\=|\?|!|#|%|@|\$)'        \
                         r'(?P<value>.*?)\}(?!\\)')
        pos = 0
        while True:
            mo = reo.search(text,pos)
            if not mo: break
            attr = mo.group()
            name =  mo.group('name')
            lval =  attrs.get(name)
            op = mo.group('op')
            # mo.end() is not good enough because '{x={y}}' matches '{x={y}'.
            end = end_brace(text,mo.start())
            rval = text[mo.start('value'):end-1]
            if lval is None:
                if op == '=': s = rval
                elif op == '?': s = ''
                elif op == '!': s = rval
                elif op == '#': s = '{'+name+'}'    # So the line is dropped.
                elif op == '%': s = rval
                elif op in ('@','$'):
                    s = '{'+name+'}'                # So the line is dropped.
                else:
                    assert False, 'illegal attribute: %s' % attr
            else:
                if op == '=': s = lval
                elif op == '?': s = rval
                elif op == '!': s = ''
                elif op == '#': s = rval
                elif op == '%': s = '{zzzzz}'       # So the line is dropped.
                elif op in ('@','$'):
                    v = re.split(r'(?<!\\):',rval)
                    if len(v) not in (2,3):
                        error('illegal attribute syntax: %s' % attr)
                        s = ''
                    elif not is_regexp('^'+v[0]+'$'):
                        error('illegal attribute regexp: %s' % attr)
                        s = ''
                    else:
                        v = [s.replace('\\:',':') for s in v]
                        re_mo = re.match('^'+v[0]+'$',lval)
                        if op == '@':
                            if re_mo:
                                s = v[1]            # {<name>@<re>:<v1>[:<v2>]}
                            else:
                                if len(v) == 3:     # {<name>@<re>:<v1>:<v2>}
                                    s = v[2]
                                else:               # {<name>@<re>:<v1>}
                                    s = ''
                        else:
                            if re_mo:
                                if len(v) == 2:     # {<name>$<re>:<v1>}
                                    s = v[1]
                                elif v[1] == '':    # {<name>$<re>::<v2>}
                                    s = '{zzzzz}'   # So the line is dropped.
                                else:               # {<name>$<re>:<v1>:<v2>}
                                    s = v[1]
                            else:
                                if len(v) == 2:     # {<name>$<re>:<v1>}
                                    s = '{zzzzz}'   # So the line is dropped.
                                else:               # {<name>$<re>:<v1>:<v2>}
                                    s = v[2]
                else:
                    assert False, 'illegal attribute: %s' % attr
            s = str(s)
            text = text[:mo.start()] + s + text[end:]
            pos = mo.start() + len(s)
        # Drop line if it contains  unsubstituted {name} references.
        skipped = re.search(r'(?su)\{[^\\\W][-\w]*?\}(?!\\)', text)
        if skipped:
            del lines[i]
            continue;
        # Expand system attributes.
        reo = re.compile(r'(?su)\{(?P<action>[^\\\W][-\w]*?):(?P<expr>.*?)\}(?!\\)')
        skipped = False
        pos = 0
        while True:
            mo = reo.search(text,pos)
            if not mo: break
            expr = mo.group('expr')
            expr = expr.replace('{\\','{')
            expr = expr.replace('}\\','}')
            s = system(mo.group('action'),expr)
            if s is None:
                skipped = True
                break
            text = text[:mo.start()] + s + text[mo.end():]
            pos = mo.start() + len(s)
        # Drop line if the action returns None.
        if skipped:
            del lines[i]
            continue;
        # Remove backslash from escaped entries.
        text = text.replace('{\\','{')
        text = text.replace('}\\','}')
        lines[i] = text
    if string_result:
        if lines:
            return '\n'.join(lines)
        else:
            return None
    else:
        return tuple(lines)

def char_encoding():
    encoding = document.attributes.get('encoding')
    if encoding:
        try:
            codecs.lookup(encoding)
        except LookupError,e:
            raise EAsciiDoc,str(e)
    return encoding

def char_len(s):
    return len(char_decode(s))

def char_decode(s):
    if char_encoding():
        try:
            return s.decode(char_encoding())
        except Exception:
            raise EAsciiDoc, \
                "'%s' codec can't decode \"%s\"" % (char_encoding(), s)
    else:
        return s

def char_encode(s):
    if char_encoding():
        return s.encode(char_encoding())
    else:
        return s

class Lex:
    """Lexical analysis routines. Static methods and attributes only."""
    prev_element = None
    prev_cursor = None
    def __init__(self):
        raise AssertionError,'no class instances allowed'
    def next():
        """Returns class of next element on the input (None if EOF).  The
        reader is assumed to be at the first line following a previous element,
        end of file or line one.  Exits with the reader pointing to the first
        line of the next element or EOF (leading blank lines are skipped)."""
        reader.skip_blank_lines()
        if reader.eof(): return None
        # Optimization: If we've already checked for an element at this
        # position return the element.
        if Lex.prev_element and Lex.prev_cursor == reader.cursor:
            return Lex.prev_element
        result = None
        # Check for Title.
        if not result and Title.isnext():
            result = Title
        # Check for Block Macro.
        if not result and macros.isnext():
            result = macros.current
        # Check for List.
        if not result and lists.isnext():
            result = lists.current
        # Check for DelimitedBlock.
        if not result and blocks.isnext():
            # Skip comment blocks.
            if 'skip' in blocks.current.options:
                blocks.current.translate()
                return Lex.next()
            else:
                result = blocks.current
        # Check for Table.
        if not result and tables.isnext():
            result = tables.current
        # Check for AttributeEntry.
        if not result and AttributeEntry.isnext():
            result = AttributeEntry
        # Check for AttributeList.
        if not result and AttributeList.isnext():
            result = AttributeList
        # Check for BlockTitle.
        if not result and BlockTitle.isnext():
            result = BlockTitle
        # If it's none of the above then it must be an Paragraph.
        if not result:
            if not paragraphs.isnext():
                raise EAsciiDoc,'paragraph expected'
            result = paragraphs.current
        # Cache answer.
        Lex.prev_cursor = reader.cursor
        Lex.prev_element = result
        return result
    next = staticmethod(next)

    # Extract the passthrough text and replace with temporary placeholders.
    def extract_passthroughs(text, passthroughs):
        # +++ passthrough.
        lq1 = r'(?P<lq>\+{3})'
        rq1 = r'\+{3}'
        reo1 = re.compile(r'(?msu)(^|[^\w+])(' + lq1 + r')' \
            + r'(?P<content>.+?)(' + rq1 + r')(?=[^\w+]|$)')
        # $$ passthrough.
        lq2 = r'(\[(?P<attrs>[^[]+?)\])?(?P<lq>\${2})'
        rq2 = r'\${2}'
        reo2 = re.compile(r'(?msu)(^|[^\w$\]])(' + lq2 + r')' \
            + r'(?P<content>.+?)(' + rq2 + r')(?=[^\w$]|$)')
        reo = reo1
        pos = 0
        while True:
            mo = reo.search(text,pos)
            if not mo:
                if reo == reo1:
                    reo = reo2
                    pos = 0
                    continue
                else:
                    break
            if text[mo.start()] == '\\':
                pos = mo.end()
            else:
                content = mo.group('content')
                if mo.group('lq') == '$$':
                    content = config.subs_specialchars(content)
                    attrs = {}
                    parse_attributes(mo.group('attrs'), attrs)
                    stag,etag = config.tag('$$passthrough', attrs)
                    if not stag:
                        etag = ''   # Drop end tag if start tag has been.
                    content = stag + content + etag
                passthroughs.append(content)
                # Tabs are expanded when the source is read so using them here
                # guarantees the placeholders are unambiguous.
                s = mo.group(1) + '\t' + str(len(passthroughs)-1) + '\t'
                text = text[:mo.start()] + s + text[mo.end():]
                pos = mo.start() + len(s)
        # Unescape escaped passthroughs.
        text = text.replace('\\+++', '+++')
        text = text.replace('\\$$', '$$')
        return text
    extract_passthroughs = staticmethod(extract_passthroughs)

    # Replace passthough placeholders with the original passthrough text.
    def restore_passthroughs(text, passthroughs):
        for i,v in enumerate(passthroughs):
            text = text.replace('\t'+str(i)+'\t', passthroughs[i], 1)
        return text
    restore_passthroughs = staticmethod(restore_passthroughs)

    def subs_1(s,options):
        """Perform substitution specified in 'options' (in 'options' order) on
        a single line 's' of text.  Returns the substituted string.
        Does not process 'attributes' or 'passthroughs' substitutions."""
        if not s:
            return s
        result = s
        for o in options:
            if o == 'specialcharacters':
                result = config.subs_specialchars(result)
            # Quoted text.
            elif o == 'quotes':
                result = subs_quotes(result)
            # Special words.
            elif o == 'specialwords':
                result = config.subs_specialwords(result)
            # Replacements.
            elif o in ('replacements','replacements2'):
                result = config.subs_replacements(result,o)
            # Inline macros.
            elif o == 'macros':
                result = macros.subs(result)
            elif o == 'callouts':
                result = macros.subs(result,callouts=True)
            else:
                raise EAsciiDoc,'illegal substitution option: %s' % o
        return result
    subs_1 = staticmethod(subs_1)

    def subs(lines,options):
        """Perform inline processing specified by 'options' (in 'options'
        order) on sequence of 'lines'."""
        if len(options) == 1:
            if options[0] == 'none':
                options = ()
            elif options[0] == 'normal':
                options = config.subsnormal
            elif options[0] == 'verbatim':
                options = config.subsverbatim
        if not lines or not options:
            return lines
        # Join lines so quoting can span multiple lines.
        para = '\n'.join(lines)
        if 'passthroughs' in options:
            passthroughs = []
            para = Lex.extract_passthroughs(para,passthroughs)
        for o in options:
            if o == 'attributes':
                # If we don't substitute attributes line-by-line then a single
                # undefined attribute will drop the entire paragraph.
                lines = subs_attrs(para.split('\n'))
                para = '\n'.join(lines)
            elif o != 'passthroughs':
                para = Lex.subs_1(para,(o,))
        if 'passthroughs' in options:
            para = Lex.restore_passthroughs(para,passthroughs)
        return para.splitlines()
    subs = staticmethod(subs)

    def set_margin(lines, margin=0):
        """Utility routine that sets the left margin to 'margin' space in a
        block of non-blank lines."""
        # Calculate width of block margin.
        lines = list(lines)
        width = len(lines[0])
        for s in lines:
            i = re.search(r'\S',s).start()
            if i < width: width = i
        # Strip margin width from all lines.
        for i in range(len(lines)):
            lines[i] = ' '*margin + lines[i][width:]
        return lines
    set_margin = staticmethod(set_margin)

#---------------------------------------------------------------------------
# Document element classes parse AsciiDoc reader input and write DocBook writer
# output.
#---------------------------------------------------------------------------
class Document:
    def __init__(self):
        self.doctype = None     # 'article','manpage' or 'book'.
        self.backend = None     # -b option argument.
        self.infile = None      # Source file name.
        self.outfile = None     # Output file name.
        self.attributes = {}
        self.level = 0          # 0 => front matter. 1,2,3 => sect1,2,3.
        self.has_errors = False # Set true if processing errors were flagged.
        self.has_warnings = False # Set true if warnings were flagged.
        self.safe = True        # Default safe mode.
    def init_attrs(self):
        # Set implicit attributes.
        d = time.localtime(time.time())
        self.attributes['localdate'] = time.strftime('%Y-%m-%d',d)
        s = time.strftime('%H:%M:%S',d)
        if time.daylight:
            self.attributes['localtime'] = s + ' ' + time.tzname[1]
        else:
            self.attributes['localtime'] = s + ' ' + time.tzname[0]
        # Attempt to convert the localtime to the output encoding.
        try:
            self.attributes['localtime'] = char_encode(
                self.attributes['localtime'].decode(
                    locale.getdefaultlocale()[1]
                )
            )
        except:
            pass
        self.attributes['asciidoc-version'] = VERSION
        self.attributes['backend'] = document.backend
        self.attributes['doctype'] = document.doctype
        self.attributes['backend-'+document.backend] = ''
        self.attributes['doctype-'+document.doctype] = ''
        self.attributes[document.backend+'-'+document.doctype] = ''
        self.attributes['asciidoc-dir'] = APP_DIR
        self.attributes['user-dir'] = USER_DIR
        if self.infile != '<stdin>':
            self.attributes['infile'] = self.infile
            self.attributes['indir'] = os.path.dirname(self.infile)
            self.attributes['docdir'] = os.path.dirname(self.infile) #DEPRECATED
            self.attributes['docname'] = os.path.splitext(
                    os.path.basename(self.infile))[0]
        if config.verbose:
            self.attributes['verbose'] = ''
        # Update with configuration file attributes.
        self.attributes.update(config.conf_attrs)
        # Update with command-line attributes.
        self.attributes.update(config.cmd_attrs)
        # Extract miscellaneous configuration section entries from attributes.
        config.load_miscellaneous(config.conf_attrs)
        config.load_miscellaneous(config.cmd_attrs)
        self.attributes['newline'] = config.newline # Use raw (unescaped) value.
        if self.outfile:
            if self.outfile != '<stdout>':
                self.attributes['outfile'] = self.outfile
                self.attributes['outdir'] = os.path.dirname(self.outfile)
                self.attributes['docname'] = os.path.splitext(
                        os.path.basename(self.outfile))[0]
                ext = os.path.splitext(self.outfile)[1][1:]
            elif config.outfilesuffix:
                ext = config.outfilesuffix[1:]
            else:
                ext = ''
            if ext:
                self.attributes['filetype'] = ext
                self.attributes['filetype-'+ext] = ''
    def translate(self):
        assert self.doctype in ('article','manpage','book'), \
            'illegal document type'
        assert self.level == 0
        config.expand_all_templates()
        # Skip leading comment block.
        if blocks.isnext() and 'skip' in blocks.current.options:
            blocks.current.translate()
        # Skip leading comment lines.
        while macros.isnext() and macros.current.name == 'comment':
            macros.current.translate()
        # Skip leading attribute entries.
        AttributeEntry.translate_all()
        # Process document header.
        has_header =  Lex.next() is Title and Title.level == 0
        if self.doctype == 'manpage' and not has_header:
            error('manpage document title is mandatory')
        if has_header:
            Header.translate()
            # Command-line entries override header derived entries.
            self.attributes.update(config.cmd_attrs)
            if config.header_footer:
                hdr = config.subs_section('header',{})
                writer.write(hdr)
            if self.doctype in ('article','book'):
                # Translate 'preamble' (untitled elements between header
                # and first section title).
                if Lex.next() is not Title:
                    stag,etag = config.section2tags('preamble')
                    writer.write(stag)
                    Section.translate_body()
                    writer.write(etag)
            else:
                # Translate manpage SYNOPSIS.
                if Lex.next() is not Title:
                    error('SYNOPSIS section expected')
                else:
                    Title.translate()
                    if Title.dict['title'].upper() <> 'SYNOPSIS':
                        error('second section must be named SYNOPSIS')
                    if Title.level != 1:
                        error('SYNOPSIS section title must be at level 1')
                    d = {}
                    d.update(Title.dict)
                    AttributeList.consume(d)
                    stag,etag = config.section2tags('sect-synopsis',d)
                    writer.write(stag)
                    Section.translate_body()
                    writer.write(etag)
        else:
            if config.header_footer:
                hdr = config.subs_section('header',{})
                writer.write(hdr)
            if Lex.next() is not Title:
                Section.translate_body()
        # Process remaining sections.
        while not reader.eof():
            if Lex.next() is not Title:
                raise EAsciiDoc,'section title expected'
            Section.translate()
        Section.setlevel(0) # Write remaining unwritten section close tags.
        # Substitute document parameters and write document footer.
        if config.header_footer:
            ftr = config.subs_section('footer',{})
            writer.write(ftr)
    def parse_author(self,s):
        """ Return False if the author is malformed."""
        attrs = self.attributes # Alias for readability.
        s = s.strip()
        mo = re.match(r'^(?P<name1>[^<>\s]+)'
                '(\s+(?P<name2>[^<>\s]+))?'
                '(\s+(?P<name3>[^<>\s]+))?'
                '(\s+<(?P<email>\S+)>)?$',s)
        if not mo:
            error('malformed author: %s' % s)
            return False
        firstname = mo.group('name1')
        if mo.group('name3'):
            middlename = mo.group('name2')
            lastname = mo.group('name3')
        else:
            middlename = None
            lastname = mo.group('name2')
        firstname = firstname.replace('_',' ')
        if middlename:
            middlename = middlename.replace('_',' ')
        if lastname:
            lastname = lastname.replace('_',' ')
        email = mo.group('email')
        if firstname:
            attrs['firstname'] = firstname
        if middlename:
            attrs['middlename'] = middlename
        if lastname:
            attrs['lastname'] = lastname
        if email:
            attrs['email'] = email
        return True
    def process_author_names(self):
        """ Calculate any missing author related attributes."""
        attrs = self.attributes # Alias for readability.
        firstname = attrs.get('firstname','')
        middlename = attrs.get('middlename','')
        lastname = attrs.get('lastname','')
        author = attrs.get('author')
        initials = attrs.get('authorinitials')
        if author and not (firstname or middlename or lastname):
            if not self.parse_author(author):
                return
            attrs['author'] = author.replace('_',' ')
            self.process_author_names()
            return
        if not author:
            author = '%s %s %s' % (firstname, middlename, lastname)
            author = author.strip()
            author = re.sub(r'\s+',' ', author)
        if not initials:
            initials = firstname[:1] + middlename[:1] + lastname[:1]
            initials = initials.upper()
        names = [firstname,middlename,lastname,author,initials]
        for i,v in enumerate(names):
            v = config.subs_specialchars(v)
            v = subs_attrs(v)
            names[i] = v
        firstname,middlename,lastname,author,initials = names
        if firstname:
            attrs['firstname'] = firstname
        if middlename:
            attrs['middlename'] = middlename
        if lastname:
            attrs['lastname'] = lastname
        if author:
            attrs['author'] = author
        if initials:
            attrs['authorinitials'] = initials
        if author:
            attrs['authored'] = ''


class Header:
    """Static methods and attributes only."""
    def __init__(self):
        raise AssertionError,'no class instances allowed'
    def translate():
        assert Lex.next() is Title and Title.level == 0
        Title.translate()
        attrs = document.attributes # Alias for readability.
        attrs['doctitle'] = Title.dict['title']
        if document.doctype == 'manpage':
            # manpage title formatted like mantitle(manvolnum).
            mo = re.match(r'^(?P<mantitle>.*)\((?P<manvolnum>.*)\)$',
                          attrs['doctitle'])
            if not mo:
                error('malformed manpage title')
            else:
                mantitle = mo.group('mantitle').strip()
                # mantitle is lowered only if in ALL CAPS
                if mantitle == mantitle.upper():
                    mantitle = mantitle.lower()
                attrs['mantitle'] = mantitle;
                attrs['manvolnum'] = mo.group('manvolnum').strip()
        AttributeEntry.translate_all()
        s = reader.read_next()
        if s:
            s = reader.read()
            document.parse_author(s)
            AttributeEntry.translate_all()
            if reader.read_next():
                # Parse revision line.
                s = reader.read()
                s = subs_attrs(s)
                if s:
                    # Match RCS/CVS/SVN $Id$ marker format.
                    mo = re.match(r'^\$Id: \S+ (?P<revision>\S+)'
                         ' (?P<date>\S+) \S+ \S+ (\S+ )?\$$',s)
                    if not mo:
                        # Match AsciiDoc revision,date format.
                        mo = re.match(r'^\D*(?P<revision>.*?),(?P<date>.+)$',s)
                    if mo:
                        revision = mo.group('revision').strip()
                        date = mo.group('date').strip()
                    else:
                        revision = None
                        date = s.strip()
                    if revision:
                        attrs['revision'] = config.subs_specialchars(revision)
                    if date:
                        attrs['date'] = config.subs_specialchars(date)
            AttributeEntry.translate_all()
        if document.doctype == 'manpage':
            # Translate mandatory NAME section.
            if Lex.next() is not Title:
                error('NAME section expected')
            else:
                Title.translate()
                if Title.dict['title'].upper() <> 'NAME':
                    error('first section must be named NAME')
                if Title.level != 1:
                    error('NAME section title must be at level 1')
                if not isinstance(Lex.next(),Paragraph):
                    error('malformed NAME section body')
                lines = reader.read_until(r'^$')
                s = ' '.join(lines)
                mo = re.match(r'^(?P<manname>.*?)\s+-\s+(?P<manpurpose>.*)$',s)
                if not mo:
                    error('malformed NAME section body')
                attrs['manname'] = mo.group('manname').strip()
                attrs['manpurpose'] = mo.group('manpurpose').strip()
        document.process_author_names()
        if document.backend == 'linuxdoc' and not attrs.has_key('author'):
            warning('linuxdoc requires author name')
    translate = staticmethod(translate)

class AttributeEntry:
    """Static methods and attributes only."""
    pattern = None
    subs = None
    name = None
    value = None
    def __init__(self):
        raise AssertionError,'no class instances allowed'
    def isnext():
        result = False  # Assume not next.
        if not AttributeEntry.pattern:
            pat = document.attributes.get('attributeentry-pattern')
            if not pat:
                error("[attributes] missing 'attributeentry-pattern' entry")
            AttributeEntry.pattern = pat
        if not AttributeEntry.subs:
            subs = document.attributes.get('attributeentry-subs')
            if subs:
                subs = parse_options(subs,SUBS_OPTIONS,
                    'illegal [%s] %s: %s' % ('attributes','attributeentry-subs',subs))
            else:
                subs = ('specialcharacters','attributes')
            AttributeEntry.subs = subs
        line = reader.read_next()
        if line:
            mo = re.match(AttributeEntry.pattern,line)
            if mo:
                name = mo.group('attrname').strip()
                if name[-1] == '!':     # Names like name! are None.
                    name = name[:-1]
                    value = None
                else:
                    value = mo.group('attrvalue').strip()
                # Strip white space and illegal name chars.
                name = re.sub(r'(?u)[^\w\-_]', '', name).lower()
                AttributeEntry.name = name
                AttributeEntry.value = value
                result = True
        return result
    isnext = staticmethod(isnext)
    def translate():
        assert Lex.next() is AttributeEntry
        attr = AttributeEntry   # Alias for brevity.
        reader.read()   # Discard attribute from reader.
        # Don't override command-line attributes.
        if config.cmd_attrs.has_key(attr.name):
            return
        # Update document.attributes from previously parsed attribute.
        if attr.value:
            attr.value = Lex.subs((attr.value,), attr.subs)
            attr.value = writer.newline.join(attr.value)
        if attr.value is not None:
            document.attributes[attr.name] = attr.value
        elif document.attributes.has_key(attr.name):
            del document.attributes[attr.name]
    translate = staticmethod(translate)
    def translate_all():
        """ Process all contiguous attribute lines on reader."""
        while AttributeEntry.isnext():
            AttributeEntry.translate()
    translate_all = staticmethod(translate_all)

class AttributeList:
    """Static methods and attributes only."""
    pattern = None
    match = None
    attrs = {}
    def __init__(self):
        raise AssertionError,'no class instances allowed'
    def isnext():
        result = False  # Assume not next.
        if not AttributeList.pattern:
            if not document.attributes.has_key('attributelist-pattern'):
                error("[attributes] missing 'attributelist-pattern' entry")
            AttributeList.pattern = document.attributes['attributelist-pattern']
        line = reader.read_next()
        if line:
            mo = re.match(AttributeList.pattern, line)
            if mo:
                AttributeList.match = mo
                result = True
        return result
    isnext = staticmethod(isnext)
    def translate():
        assert Lex.next() is AttributeList
        reader.read()   # Discard attribute list from reader.
        d = AttributeList.match.groupdict()
        for k,v in d.items():
            if v is not None:
                if k == 'attrlist':
                    v = subs_attrs(v)
                    if v:
                        parse_attributes(v, AttributeList.attrs)
                else:
                    AttributeList.attrs[k] = v
    translate = staticmethod(translate)
    def consume(d):
        """Add attribute list to the dictionary 'd' and reset the
        list."""
        if AttributeList.attrs:
            d.update(AttributeList.attrs)
            AttributeList.attrs = {}
    consume = staticmethod(consume)

class BlockTitle:
    """Static methods and attributes only."""
    title = None
    pattern = None
    def __init__(self):
        raise AssertionError,'no class instances allowed'
    def isnext():
        result = False  # Assume not next.
        line = reader.read_next()
        if line:
            mo = re.match(BlockTitle.pattern,line)
            if mo:
                BlockTitle.title = mo.group('title')
                result = True
        return result
    isnext = staticmethod(isnext)
    def translate():
        assert Lex.next() is BlockTitle
        reader.read()   # Discard title from reader.
        # Perform title substitutions.
        if not Title.subs:
            Title.subs = config.subsnormal
        s = Lex.subs((BlockTitle.title,), Title.subs)
        s = writer.newline.join(s)
        if not s:
            warning('blank block title')
        BlockTitle.title = s
    translate = staticmethod(translate)
    def consume(d):
        """If there is a title add it to dictionary 'd' then reset title."""
        if BlockTitle.title:
            d['title'] = BlockTitle.title
            BlockTitle.title = None
    consume = staticmethod(consume)

class Title:
    """Processes Header and Section titles. Static methods and attributes
    only."""
    # Class variables
    underlines = ('==','--','~~','^^','++') # Levels 0,1,2,3,4.
    subs = ()
    pattern = None
    level = 0
    dict = {}
    sectname = None
    section_numbers = [0]*len(underlines)
    dump_dict = {}
    linecount = None    # Number of lines in title (1 or 2).
    def __init__(self):
        raise AssertionError,'no class instances allowed'
    def translate():
        """Parse the Title.dict and Title.level from the reader. The
        real work has already been done by parse()."""
        assert Lex.next() is Title
        # Discard title from reader.
        for i in range(Title.linecount):
            reader.read()
        Title.setsectname()
        # Perform title substitutions.
        if not Title.subs:
            Title.subs = config.subsnormal
        s = Lex.subs((Title.dict['title'],), Title.subs)
        s = writer.newline.join(s)
        if not s:
            warning('blank section title')
        Title.dict['title'] = s
    translate = staticmethod(translate)
    def isnext():
        lines = reader.read_ahead(2)
        return Title.parse(lines)
    isnext = staticmethod(isnext)
    def parse(lines):
        """Parse title at start of lines tuple."""
        if len(lines) == 0: return False
        if len(lines[0]) == 0: return False # Title can't be blank.
        # Check for single-line titles.
        result = False
        for level in range(len(Title.underlines)):
            k = 'sect%s' % level
            if Title.dump_dict.has_key(k):
                mo = re.match(Title.dump_dict[k], lines[0])
                if mo:
                    Title.dict = mo.groupdict()
                    Title.level = level
                    Title.linecount = 1
                    result = True
                    break
        if not result:
            # Check for double-line titles.
            if not Title.pattern: return False  # Single-line titles only.
            if len(lines) < 2: return False
            title,ul = lines[:2]
            title_len = char_len(title)
            ul_len = char_len(ul)
            if ul_len < 2: return False
            # Fast elimination check.
            if ul[:2] not in Title.underlines: return False
            # Length of underline must be within +-3 of title.
            if not (ul_len-3 < title_len < ul_len+3): return False
            # Check for valid repetition of underline character pairs.
            s = ul[:2]*((ul_len+1)/2)
            if ul != s[:ul_len]: return False
            # Don't be fooled by back-to-back delimited blocks, require at
            # least one alphanumeric character in title.
            if not re.search(r'(?u)\w',title): return False
            mo = re.match(Title.pattern, title)
            if mo:
                Title.dict = mo.groupdict()
                Title.level = list(Title.underlines).index(ul[:2])
                Title.linecount = 2
                result = True
        # Check for expected pattern match groups.
        if result:
            if not Title.dict.has_key('title'):
                warning('[titles] entry has no <title> group')
                Title.dict['title'] = lines[0]
            for k,v in Title.dict.items():
                if v is None: del Title.dict[k]
        return result
    parse = staticmethod(parse)
    def load(dict):
        """Load and validate [titles] section entries from dict."""
        if dict.has_key('underlines'):
            errmsg = 'malformed [titles] underlines entry'
            try:
                underlines = parse_list(dict['underlines'])
            except:
                raise EAsciiDoc,errmsg
            if len(underlines) != len(Title.underlines):
                raise EAsciiDoc,errmsg
            for s in underlines:
                if len(s) !=2:
                    raise EAsciiDoc,errmsg
            Title.underlines = tuple(underlines)
            Title.dump_dict['underlines'] = dict['underlines']
        if dict.has_key('subs'):
            Title.subs = parse_options(dict['subs'], SUBS_OPTIONS,
                'illegal [titles] subs entry')
            Title.dump_dict['subs'] = dict['subs']
        if dict.has_key('sectiontitle'):
            pat = dict['sectiontitle']
            if not pat or not is_regexp(pat):
                raise EAsciiDoc,'malformed [titles] sectiontitle entry'
            Title.pattern = pat
            Title.dump_dict['sectiontitle'] = pat
        if dict.has_key('blocktitle'):
            pat = dict['blocktitle']
            if not pat or not is_regexp(pat):
                raise EAsciiDoc,'malformed [titles] blocktitle entry'
            BlockTitle.pattern = pat
            Title.dump_dict['blocktitle'] = pat
        # Load single-line title patterns.
        for k in ('sect0','sect1','sect2','sect3','sect4'):
            if dict.has_key(k):
                pat = dict[k]
                if not pat or not is_regexp(pat):
                    raise EAsciiDoc,'malformed [titles] %s entry' % k
                Title.dump_dict[k] = pat
        # TODO: Check we have either a Title.pattern or at least one
        # single-line title pattern -- can this be done here or do we need
        # check routine like the other block checkers?
    load = staticmethod(load)
    def dump():
        dump_section('titles',Title.dump_dict)
    dump = staticmethod(dump)
    def setsectname():
        """Set Title section name. First search for section title in
        [specialsections], if not found use default 'sect<level>' name."""
        for pat,sect in config.specialsections.items():
            mo = re.match(pat,Title.dict['title'])
            if mo:
                title = mo.groupdict().get('title')
                if title is not None:
                    Title.dict['title'] = title.strip()
                else:
                    Title.dict['title'] = mo.group().strip()
                Title.sectname = sect
                break
        else:
            Title.sectname = 'sect%d' % Title.level
    setsectname = staticmethod(setsectname)
    def getnumber(level):
        """Return next section number at section 'level' formatted like
        1.2.3.4."""
        number = ''
        for l in range(len(Title.section_numbers)):
            n = Title.section_numbers[l]
            if l == 0:
                continue
            elif l < level:
                number = '%s%d.' % (number, n)
            elif l == level:
                number = '%s%d.' % (number, n + 1)
                Title.section_numbers[l] = n + 1
            elif l > level:
                # Reset unprocessed section levels.
                Title.section_numbers[l] = 0
        return number
    getnumber = staticmethod(getnumber)


class Section:
    """Static methods and attributes only."""
    endtags = []  # Stack of currently open section (level,endtag) tuples.
    ids = []      # List of already used ids.
    def __init__(self):
        raise AssertionError,'no class instances allowed'
    def savetag(level,etag):
        """Save section end."""
        Section.endtags.append((level,etag))
    savetag = staticmethod(savetag)
    def setlevel(level):
        """Set document level and write open section close tags up to level."""
        while Section.endtags and Section.endtags[-1][0] >= level:
            writer.write(Section.endtags.pop()[1])
        document.level = level
    setlevel = staticmethod(setlevel)
    def gen_id(title):
        """
        The normalized value of the id attribute is an NCName according to
        the 'Namespaces in XML' Recommendation:
        NCName          ::=     NCNameStartChar NCNameChar*
        NCNameChar      ::=     NameChar - ':'
        NCNameStartChar ::=     Letter | '_'
        NameChar        ::=     Letter | Digit | '.' | '-' | '_' | ':'
        """
        base_ident = re.sub(r'[^a-zA-Z0-9]+', '_', title).strip('_').lower()
        # Prefix with underscore to ensure a valid id start character and to
        # ensure the id does not clash with existing document id's.
        base_ident = '_' + base_ident
        i = 1
        while True:
            if i == 1:
                ident = base_ident
            else:
                ident = '%s_%d' % (base_ident, i)
            if ident not in Section.ids:
                Section.ids.append(ident)
                return ident
            else:
                ident = base_ident
            i += 1
    gen_id = staticmethod(gen_id)
    def translate():
        assert Lex.next() is Title
        prev_sectname = Title.sectname
        Title.translate()
        if Title.level == 0 and document.doctype != 'book':
            error('only book doctypes can contain level 0 sections')
        if Title.level > document.level \
                and document.backend == 'docbook' \
                and prev_sectname in ('sect-colophon','sect-abstract', \
                    'sect-dedication','sect-glossary','sect-bibliography'):
            error('%s section cannot contain sub-sections' % prev_sectname)
        if Title.level > document.level+1:
            # Sub-sections of multi-part book level zero Preface and Appendices
            # are meant to be out of sequence.
            if document.doctype == 'book' \
                    and document.level == 0 \
                    and Title.level == 2 \
                    and prev_sectname in ('sect-preface','sect-appendix'):
                pass
            else:
                warning('section title out of sequence: '
                    'expected level %d, got level %d'
                    % (document.level+1, Title.level))
        if not document.attributes.get('sectids') is None \
                and 'id' not in AttributeList.attrs:
            # Generate ids for sections.
            AttributeList.attrs['id'] = Section.gen_id(Title.dict['title'])
        Section.setlevel(Title.level)
        Title.dict['sectnum'] = Title.getnumber(document.level)
        AttributeList.consume(Title.dict)
        stag,etag = config.section2tags(Title.sectname,Title.dict)
        Section.savetag(Title.level,etag)
        writer.write(stag)
        Section.translate_body()
    translate = staticmethod(translate)
    def translate_body(terminator=Title):
        isempty = True
        next = Lex.next()
        while next and next is not terminator:
            if next is Title and isinstance(terminator,DelimitedBlock):
                error('title not permitted in sidebar body')
            if document.backend == 'linuxdoc'   \
                and document.level == 0         \
                and not isinstance(next,Paragraph):
                warning('only paragraphs are permitted in linuxdoc synopsis')
            next.translate()
            next = Lex.next()
            isempty = False
        # The section is not empty if contains a subsection.
        if next and isempty and Title.level > document.level:
            isempty = False
        # Report empty sections if invalid markup will result.
        if isempty:
            if document.backend == 'docbook' and Title.sectname != 'sect-index':
                error('empty section is not valid')
    translate_body = staticmethod(translate_body)

class AbstractBlock:
    def __init__(self):
        self.OPTIONS = ()   # The set of allowed options values
        # Configuration parameter names common to all blocks.
        self.CONF_ENTRIES = ('options','subs','presubs','postsubs',
                             'posattrs','style','.*-style')
        # Configuration parameters.
        self.name=None      # Configuration file section name.
        self.delimiter=None # Regular expression matching block delimiter.
        self.template=None  # template section entry.
        self.options=()     # options entry list.
        self.presubs=None   # presubs/subs entry list.
        self.postsubs=()    # postsubs entry list.
        self.filter=None    # filter entry.
        self.posattrs=()    # posattrs entry list.
        self.style=None     # Default style.
        self.styles=OrderedDict()   # Styles dictionary.
        # Before a block is processed it's attributes (from it's
        # attributes list) are merged with the block configuration parameters
        # (by self.process_attributes()) resulting in the template substitution
        # dictionary (self.attributes) and the block's procssing parameters
        # (self.parameters).
        self.attributes={}
        # The names of block parameters.
        self.PARAM_NAMES=('template','options','presubs','postsubs','filter')
        self.parameters={}
        # Leading delimiter match object.
        self.mo=None
    def is_conf_entry(self,param):
        """Return True if param matches an allowed configuration file entry
        name."""
        for s in self.CONF_ENTRIES:
            if re.match('^'+s+'$',param):
                return True
        return False
    def load(self,name,entries):
        """Update block definition from section 'entries' dictionary."""
        for k in entries.keys():
            if not self.is_conf_entry(k):
                raise EAsciiDoc,'illegal [%s] entry name: %s' % (name,k)
        self.name = name
        for k,v in entries.items():
            if not is_name(k):
                raise EAsciiDoc, \
                    'malformed [%s] entry name: %s' % (name,k)
            if k == 'delimiter':
                if v and is_regexp(v):
                    self.delimiter = v
                else:
                    raise EAsciiDoc,'malformed [%s] regexp: %s' % (name,v)
            elif k == 'template':
                if not is_name(v):
                    raise EAsciiDoc, \
                        'malformed [%s] template name: %s' % (name,v)
                self.template = v
            elif k == 'style':
                if not is_name(v):
                    raise EAsciiDoc, \
                        'malformed [%s] style name: %s' % (name,v)
                self.style = v
            elif k == 'posattrs':
                self.posattrs = parse_options(v, (),
                    'illegal [%s] %s: %s' % (name,k,v))
            elif k == 'options':
                self.options = parse_options(v,self.OPTIONS,
                    'illegal [%s] %s: %s' % (name,k,v))
            elif k == 'presubs' or k == 'subs':
                self.presubs = parse_options(v,SUBS_OPTIONS,
                    'illegal [%s] %s: %s' % (name,k,v))
            elif k == 'postsubs':
                self.postsubs = parse_options(v,SUBS_OPTIONS,
                    'illegal [%s] %s: %s' % (name,k,v))
            elif k == 'filter':
                self.filter = v
            else:
                mo = re.match(r'^(?P<style>.*)-style$',k)
                if mo:
                    if not v:
                        raise EAsciiDoc, 'empty [%s] style: %s' % (name,k)
                    style = mo.group('style')
                    d = {}
                    if not parse_named_attributes(v,d):
                        raise EAsciiDoc,'malformed [%s] style: %s' % (name,v)
                    self.styles[style] = d
    def dump(self):
        """Write block definition to stdout."""
        write = lambda s: sys.stdout.write('%s%s' % (s,writer.newline))
        write('['+self.name+']')
        if self.is_conf_entry('delimiter'):
            write('delimiter='+self.delimiter)
        if self.template:
            write('template='+self.template)
        if self.options:
            write('options='+','.join(self.options))
        if self.presubs:
            if self.postsubs:
                write('presubs='+','.join(self.presubs))
            else:
                write('subs='+','.join(self.presubs))
        if self.postsubs:
            write('postsubs='+','.join(self.postsubs))
        if self.filter:
            write('filter='+self.filter)
        if self.posattrs:
            write('posattrs='+','.join(self.posattrs))
        if self.style:
            write('style='+self.style)
        if self.styles:
            for style,d in self.styles.items():
                s = ''
                for k,v in d.items(): s += '%s=%r,' % (k,v)
                write('%s-style=%s' % (style,s[:-1]))
    def validate(self):
        """Validate block after the complete configuration has been loaded."""
        if self.is_conf_entry('delimiter') and not self.delimiter:
            raise EAsciiDoc,'[%s] missing delimiter' % self.name
        if self.style:
            if not self.styles.has_key(self.style):
                warning(' missing [%s] %s-style entry' % (self.name,self.style))
        # Check all styles for missing templates.
        all_styles_have_template = True
        for k,v in self.styles.items():
            t = v.get('template')
            if t and not config.sections.has_key(t):
                warning('[%s] missing template section' % t)
            if not t:
                all_styles_have_template = False
        # Check we have a valid template entry or alternatively that all the
        # styles have templates.
        if self.is_conf_entry('template') and not 'skip' in self.options:
            if self.template:
                if not config.sections.has_key(self.template):
                    warning('[%s] missing template section' % self.template)
            elif not all_styles_have_template:
                warning('[%s] styles missing templates' % self.name)
    def isnext(self):
        """Check if this block is next in document reader."""
        result = False
        reader.skip_blank_lines()
        if reader.read_next():
            mo = re.match(self.delimiter,reader.read_next())
            if mo:
                self.mo = mo
                result = True
        return result
    def translate(self):
        """Translate block from document reader."""
        if not self.presubs:
            self.presubs = config.subsnormal
    def update_params(self,src,dst):
        """Copy block processing parameters from src to dst dictionaries."""
        for k,v in src.items():
            if k in ('template','filter'):
                dst[k] = v
            elif k == 'options':
                dst[k] = parse_options(v,self.OPTIONS,
                    'illegal [%s] %s: %s' % (self.name,k,v))
            elif k in  ('subs','presubs','postsubs'):
                subs = parse_options(v,SUBS_OPTIONS,
                    'illegal [%s] %s: %s' % (self.name,k,v))
                if k == 'subs':
                    dst['presubs'] = subs
                else:
                    dst[k] = subs
    def merge_attributes(self,attrs):
        """Merge block attributes 'attrs' dictionary with the block
        configuration parameters setting self.attributes (template substitution
        attributes) and self.parameters (block processing parameters)."""
        self.attributes = {}
        self.attributes.update(attrs)
        # Calculate dynamic block parameters.
        # Start with configuration file defaults.
        self.parameters['template'] = self.template
        self.parameters['options'] = self.options
        self.parameters['presubs'] = self.presubs
        self.parameters['postsubs'] = self.postsubs
        self.parameters['filter'] = self.filter
        # Load the selected style attributes.
        posattrs = self.posattrs
        if posattrs and posattrs[0] == 'style':
            style = self.attributes.get('1')
        else:
            style = None
        if not style:
            style = self.attributes.get('style',self.style)
        if style is not None:
            if not self.styles.has_key(style):
                warning('missing [%s] %s-style entry' % (self.name,style))
            else:
                self.attributes['style'] = style
                for k,v in self.styles[style].items():
                    if k == 'posattrs':
                        posattrs = v
                    elif k in self.PARAM_NAMES:
                        self.parameters[k] = v
                    elif not self.attributes.has_key(k):
                        # Style attributes don't take precedence over explicit.
                        self.attributes[k] = v
        # Set named positional attributes.
        for i,v in enumerate(posattrs):
            if self.attributes.has_key(str(i+1)):
                self.attributes[v] = self.attributes[str(i+1)]
        # Override config and style attributes with document attributes.
        self.update_params(self.attributes,self.parameters)
        assert isinstance(self.parameters['options'],tuple)
        assert isinstance(self.parameters['presubs'],tuple)
        assert isinstance(self.parameters['postsubs'],tuple)
    def get_options(self):
        return self.parameters['options']
    def get_subs(self):
        return (self.parameters['presubs'], self.parameters['postsubs'])
    def get_template(self):
        return self.parameters['template']
    def get_filter(self):
        return self.parameters['filter']

class AbstractBlocks:
    """List of block definitions."""
    PREFIX = ''         # Conf file section name prefix set in derived classes.
    BLOCK_TYPE = None   # Block type set in derived classes.
    def __init__(self):
        self.current=None
        self.blocks = []        # List of Block objects.
        self.default = None     # Default Block.
        self.delimiter = None   # Combined tables delimiter regular expression.
    def load(self,sections):
        """Load block definition from 'sections' dictionary."""
        for k in sections.keys():
            if re.match(r'^'+ self.PREFIX + r'.+$',k):
                d = {}
                parse_entries(sections.get(k,()),d)
                for b in self.blocks:
                    if b.name == k:
                        break
                else:
                    b = self.BLOCK_TYPE()
                    self.blocks.append(b)
                try:
                    b.load(k,d)
                except EAsciiDoc,e:
                    raise EAsciiDoc,'[%s] %s' % (k,str(e))
    def dump(self):
        for b in self.blocks:
            b.dump()
    def isnext(self):
        for b in self.blocks:
            if b.isnext():
                self.current = b
                return True;
        return False
    def validate(self):
        """Validate the block definitions."""
        # Validate delimiters and build combined lists delimiter pattern.
        delimiters = []
        for b in self.blocks:
            assert b.__class__ is self.BLOCK_TYPE
            b.validate()
            if b.delimiter:
                delimiters.append(b.delimiter)
        self.delimiter = join_regexp(delimiters)

class Paragraph(AbstractBlock):
    def __init__(self):
        AbstractBlock.__init__(self)
        self.CONF_ENTRIES += ('delimiter','template','filter')
        self.OPTIONS = ('listelement',)
        self.text=None      # Text in first line of paragraph.
    def load(self,name,entries):
        AbstractBlock.load(self,name,entries)
    def dump(self):
        AbstractBlock.dump(self)
        write = lambda s: sys.stdout.write('%s%s' % (s,writer.newline))
        write('')
    def isnext(self):
        result = AbstractBlock.isnext(self)
        if result:
            self.text = self.mo.groupdict().get('text')
        return result
    def translate(self):
        AbstractBlock.translate(self)
        attrs = {}
        attrs.update(self.mo.groupdict())
        BlockTitle.consume(attrs)
        AttributeList.consume(attrs)
        self.merge_attributes(attrs)
        reader.read()   # Discard (already parsed item first line).
        body = reader.read_until(r'^\+$|^$|'+blocks.delimiter+r'|'+tables.delimiter)
        body = [self.text] + list(body)
        presubs,postsubs = self.get_subs()
        # Don't join verbatim paragraphs.
        if 'verbatim' not in (presubs + postsubs):
            body = join_lines(body)
        body = Lex.set_margin(body) # Move body to left margin.
        body = Lex.subs(body,presubs)
        if self.get_filter():
            body = filter_lines(self.get_filter(),body,self.attributes)
        body = Lex.subs(body,postsubs)
        template = self.get_template()
        stag,etag = config.section2tags(template, self.attributes)
        # Write start tag, content, end tag.
        writer.write(dovetail_tags(stag,body,etag))

class Paragraphs(AbstractBlocks):
    """List of paragraph definitions."""
    BLOCK_TYPE = Paragraph
    PREFIX = 'paradef-'
    def __init__(self):
        AbstractBlocks.__init__(self)
    def load(self,sections):
        AbstractBlocks.load(self,sections)
    def validate(self):
        AbstractBlocks.validate(self)
        # Check we have a default paragraph definition, put it last in list.
        for b in self.blocks:
            if b.name == 'paradef-default':
                self.blocks.append(b)
                self.default = b
                self.blocks.remove(b)
                break
        else:
            raise EAsciiDoc,'missing [paradef-default] section'

class List(AbstractBlock):
    TAGS = ('listtag','itemtag','texttag','entrytag','labeltag')
    TYPES = ('bulleted','numbered','labeled','callout')
    def __init__(self):
        AbstractBlock.__init__(self)
        self.CONF_ENTRIES += ('delimiter','type') + self.TAGS
        self.listtag=None
        self.itemtag=None
        self.texttag=None   # Tag for list item text.
        self.labeltag=None  # Variable lists only.
        self.entrytag=None  # Variable lists only.
        self.label=None     # List item label (labeled lists).
        self.text=None      # Text in first line of list item.
        self.index=None     # Matched delimiter 'index' group (numbered lists).
        self.type=None      # List type.
        self.listindex=None # Current list index (1..)
    def load(self,name,entries):
        AbstractBlock.load(self,name,entries)
        for k,v in entries.items():
            if k == 'type':
                if v in self.TYPES:
                    self.type = v
                else:
                    raise EAsciiDoc,'illegal list type: %s' % v
            elif k in self.TAGS:
                if is_name(v):
                    setattr(self,k,v)
                else:
                    raise EAsciiDoc,'illegal list %s name: %s' % (k,v)
    def dump(self):
        AbstractBlock.dump(self)
        write = lambda s: sys.stdout.write('%s%s' % (s,writer.newline))
        write('type='+self.type)
        write('listtag='+self.listtag)
        write('itemtag='+self.itemtag)
        write('texttag='+self.texttag)
        if self.type == 'labeled':
            write('entrytag='+self.entrytag)
            write('labeltag='+self.labeltag)
        write('')
    def isnext(self):
        result = AbstractBlock.isnext(self)
        if result:
            self.label = self.mo.groupdict().get('label')
            self.text = self.mo.groupdict().get('text')
            self.index = self.mo.groupdict().get('index')
        return result
    def translate_entry(self):
        assert self.type == 'labeled'
        stag,etag = config.tag(self.entrytag, self.attributes)
        if stag:
            writer.write(stag)
        if self.listtag == 'hlist':
            # Horizontal label list.
            reader.read()   # Discard (already parsed item first line).
            writer.write_tag(self.labeltag, [self.label],
                             self.presubs, self.attributes)
        else:
            # Write multiple labels (vertical label list).
            while Lex.next() is self:
                reader.read()   # Discard (already parsed item first line).
                writer.write_tag(self.labeltag, [self.label],
                                 self.presubs, self.attributes)
        # Write item text.
        self.translate_item()
        if etag:
            writer.write(etag)
    def iscontinued(self):
        if reader.read_next() == '+':
            reader.read()   # Discard.
            # Allow attribute list to precede continued list item element.
            while Lex.next() is AttributeList:
                Lex.next().translate()
            return True
        else:
            return False
    def translate_item(self):
        if lists.listblock:
            self.translate_item_2()
        else:
            self.translate_item_1()
    def translate_item_1(self):
        """Translation for '+' style list continuation."""
        if self.type == 'callout':
            self.attributes['coids'] = calloutmap.calloutids(self.listindex)
        stag,etag = config.tag(self.itemtag, self.attributes)
        if stag:
            writer.write(stag)
        if self.text and self.text == '+':
            # Pathalogical case: continued Horizontal Labeled List with no
            # item text.
            continued = True
        elif not self.text and self.iscontinued():
            # Pathalogical case: continued Vertical Labeled List with no
            # item text.
            continued = True
        else:
            # Write ItemText.
            text = reader.read_until(lists.delimiter + r'|^\+$|^$|' +
                                    blocks.delimiter + r'|' + tables.delimiter)
            if self.text is not None:
                text = [self.text] + list(text)
            text = join_lines(text)
            if text:
                writer.write_tag(self.texttag, text, self.presubs, self.attributes)
            continued = self.iscontinued()
        while True:
            next = Lex.next()
            if next in lists.open:
                break
            elif isinstance(next,List):
                next.translate()
            elif isinstance(next,Paragraph) and 'listelement' in next.options:
                next.translate()
            elif continued:
                if next is Title or next is BlockTitle:
                    error('title not allowed in list item continuation')
                next.translate()
            else:
                break
            continued = self.iscontinued()
        if etag:
            writer.write(etag)
    def translate_item_2(self):
        """Translation for List block style lists."""
        if self.type == 'callout':
            self.attributes['coids'] = calloutmap.calloutids(self.listindex)
        stag,etag = config.tag(self.itemtag, self.attributes)
        if stag:
            writer.write(stag)
        if self.text or reader.read_next():
            # Write ItemText.
            text = reader.read_until(lists.delimiter + r'|^$|' +
                                    blocks.delimiter + r'|' + tables.delimiter)
            if self.text is not None:
                text = [self.text] + list(text)
            text = join_lines(text)
            writer.write_tag(self.texttag, text, self.presubs, self.attributes)
        while True:
            next = Lex.next()
            if next in lists.open:
                break
            elif next is lists.listblock:
                break
            elif isinstance(next,List):
                next.translate()
            elif isinstance(next,Paragraph) and 'listelement' in next.options:
                next.translate()
            elif lists.listblock:
                if next is Title or next is BlockTitle:
                    error('title not allowed in list item continuation')
                next.translate()
            else:
                break
        if etag:
            writer.write(etag)
    def check_index(self):
        """ Check calculated listindex (1,2,...) against the item index in the
        document (self.index)."""
        assert self.type in ('numbered','callout')
        if self.index:
            matched = False
            if re.match(r'\d+', self.index):
                i = int(self.index)
                matched = True
            elif re.match(r'[a-z]', self.index):
                i = ord(self.index) - ord('a') + 1
                matched = True
            if matched and i != self.listindex:
                print 'type: ',self.type,': expected ',self.listindex,' got ',i
                warning('list item %s out of sequence' % self.index)
    def translate(self):
        AbstractBlock.translate(self)
        lists.open.append(self)
        attrs = {}
        attrs.update(self.mo.groupdict())
        BlockTitle.consume(attrs)
        AttributeList.consume(attrs)
        self.merge_attributes(attrs)
        stag,etag = config.tag(self.listtag, self.attributes)
        if stag:
            writer.write(stag)
        self.listindex = 0
        while Lex.next() is self:
            self.listindex += 1
            document.attributes['listindex'] = str(self.listindex)
            if self.type in ('numbered','callout'):
                self.check_index()
            if self.type in ('bulleted','numbered','callout'):
                reader.read()   # Discard (already parsed item first line).
                self.translate_item()
            elif self.type == 'labeled':
                self.translate_entry()
            else:
                raise AssertionError,'illegal [%s] list type' % self.name
        if etag:
            writer.write(etag)
        if self.type == 'callout':
            calloutmap.validate(self.listindex)
            calloutmap.listclose()
        lists.open.pop()
        if len(lists.open):
            document.attributes['listindex'] = str(lists.open[-1].listindex)

class Lists(AbstractBlocks):
    """List of List objects."""
    BLOCK_TYPE = List
    PREFIX = 'listdef-'
    def __init__(self):
        AbstractBlocks.__init__(self)
        self.open = []           # A stack of the current and parent lists.
        self.listblock = None    # Current list is in list block.
    def load(self,sections):
        AbstractBlocks.load(self,sections)
    def validate(self):
        AbstractBlocks.validate(self)
        for b in self.blocks:
            # Check list has valid type.
            if not b.type in b.TYPES:
                raise EAsciiDoc,'[%s] illegal type' % b.name
            # Check all list tags.
            if not b.listtag or not config.tags.has_key(b.listtag):
                warning('[%s] missing listtag' % b.name)
            if not b.itemtag or not config.tags.has_key(b.itemtag):
                warning('[%s] missing tag itemtag' % b.name)
            if not b.texttag or not config.tags.has_key(b.texttag):
                warning('[%s] missing tag texttag' % b.name)
            if b.type == 'labeled':
                if not b.entrytag or not config.tags.has_key(b.entrytag):
                    warning('[%s] missing entrytag' % b.name)
                if not b.labeltag or not config.tags.has_key(b.labeltag):
                    warning('[%s] missing labeltag' % b.name)

class DelimitedBlock(AbstractBlock):
    def __init__(self):
        AbstractBlock.__init__(self)
        self.CONF_ENTRIES += ('delimiter','template','filter')
        self.OPTIONS = ('skip','sectionbody','list')
        self.start = None   # File reader cursor at start delimiter.
    def load(self,name,entries):
        AbstractBlock.load(self,name,entries)
    def dump(self):
        AbstractBlock.dump(self)
        write = lambda s: sys.stdout.write('%s%s' % (s,writer.newline))
        write('')
    def isnext(self):
        return AbstractBlock.isnext(self)
    def translate(self):
        AbstractBlock.translate(self)
        if 'list' in self.options:
            lists.listblock = self
        reader.read()   # Discard delimiter.
        self.start = reader.cursor[:]
        attrs = {}
        # Leave list block attributes for the list element.
        if lists.listblock is not self:
            BlockTitle.consume(attrs)
            AttributeList.consume(attrs)
        self.merge_attributes(attrs)
        options = self.get_options()
        if safe() and self.name == 'blockdef-backend':
            unsafe_error('Backend Block')
            # Discard block body.
            reader.read_until(self.delimiter,same_file=True)
        elif 'skip' in options:
            # Discard block body.
            reader.read_until(self.delimiter,same_file=True)
        else:
            template = self.get_template()
            stag,etag = config.section2tags(template,self.attributes)
            if 'sectionbody' in options or 'list' in options:
                # The body is treated like a SimpleSection.
                writer.write(stag)
                Section.translate_body(self)
                writer.write(etag)
            else:
                body = reader.read_until(self.delimiter,same_file=True)
                presubs,postsubs = self.get_subs()
                body = Lex.subs(body,presubs)
                if self.get_filter():
                    body = filter_lines(self.get_filter(),body,self.attributes)
                body = Lex.subs(body,postsubs)
                # Write start tag, content, end tag.
                writer.write(dovetail_tags(stag,body,etag))
        if 'list' in options:
            lists.listblock = None
        if reader.eof():
            error('missing %s block closing delimiter' % self.name.split('-')[-1],
                  cursor=self.start)
        else:
            delimiter = reader.read()   # Discard delimiter line.
            assert re.match(self.delimiter,delimiter)

class DelimitedBlocks(AbstractBlocks):
    """List of delimited blocks."""
    BLOCK_TYPE = DelimitedBlock
    PREFIX = 'blockdef-'
    def __init__(self):
        AbstractBlocks.__init__(self)
    def load(self,sections):
        """Update blocks defined in 'sections' dictionary."""
        AbstractBlocks.load(self,sections)
    def validate(self):
        AbstractBlocks.validate(self)

class Column:
    """Table column."""
    def __init__(self):
        self.colalign = None    # 'left','right','center'
        self.rulerwidth = None
        self.colwidth = None    # Output width in page units.

class Table(AbstractBlock):
    COL_STOP = r"(`|'|\.)"  # RE.
    ALIGNMENTS = {'`':'left', "'":'right', '.':'center'}
    FORMATS = ('fixed','csv','dsv')
    def __init__(self):
        AbstractBlock.__init__(self)
        self.CONF_ENTRIES += ('template','fillchar','format','colspec',
                              'headrow','footrow','bodyrow','headdata',
                              'footdata', 'bodydata')
        # Configuration parameters.
        self.fillchar=None
        self.format=None    # 'fixed','csv','dsv'
        self.colspec=None
        self.headrow=None
        self.footrow=None
        self.bodyrow=None
        self.headdata=None
        self.footdata=None
        self.bodydata=None
        # Calculated parameters.
        self.underline=None     # RE matching current table underline.
        self.isnumeric=False    # True if numeric ruler.
        self.tablewidth=None    # Optional table width scale factor.
        self.columns=[]         # List of Columns.
        # Other.
        self.check_msg=''       # Message set by previous self.validate() call.
    def load(self,name,entries):
        AbstractBlock.load(self,name,entries)
        """Update table definition from section entries in 'entries'."""
        for k,v in entries.items():
            if k == 'fillchar':
                if v and len(v) == 1:
                    self.fillchar = v
                else:
                    raise EAsciiDoc,'malformed table fillchar: %s' % v
            elif k == 'format':
                if v in Table.FORMATS:
                    self.format = v
                else:
                    raise EAsciiDoc,'illegal table format: %s' % v
            elif k == 'colspec':
                self.colspec = v
            elif k == 'headrow':
                self.headrow = v
            elif k == 'footrow':
                self.footrow = v
            elif k == 'bodyrow':
                self.bodyrow = v
            elif k == 'headdata':
                self.headdata = v
            elif k == 'footdata':
                self.footdata = v
            elif k == 'bodydata':
                self.bodydata = v
    def dump(self):
        AbstractBlock.dump(self)
        write = lambda s: sys.stdout.write('%s%s' % (s,writer.newline))
        write('fillchar='+self.fillchar)
        write('format='+self.format)
        if self.colspec:
            write('colspec='+self.colspec)
        if self.headrow:
            write('headrow='+self.headrow)
        if self.footrow:
            write('footrow='+self.footrow)
        write('bodyrow='+self.bodyrow)
        if self.headdata:
            write('headdata='+self.headdata)
        if self.footdata:
            write('footdata='+self.footdata)
        write('bodydata='+self.bodydata)
        write('')
    def validate(self):
        AbstractBlock.validate(self)
        """Check table definition and set self.check_msg if invalid else set
        self.check_msg to blank string."""
        # Check global table parameters.
        if config.textwidth is None:
            self.check_msg = 'missing [miscellaneous] textwidth entry'
        elif config.pagewidth is None:
            self.check_msg = 'missing [miscellaneous] pagewidth entry'
        elif config.pageunits is None:
            self.check_msg = 'missing [miscellaneous] pageunits entry'
        elif self.headrow is None:
            self.check_msg = 'missing headrow entry'
        elif self.footrow is None:
            self.check_msg = 'missing footrow entry'
        elif self.bodyrow is None:
            self.check_msg = 'missing bodyrow entry'
        elif self.headdata is None:
            self.check_msg = 'missing headdata entry'
        elif self.footdata is None:
            self.check_msg = 'missing footdata entry'
        elif self.bodydata is None:
            self.check_msg = 'missing bodydata entry'
        else:
            # No errors.
            self.check_msg = ''
    def isnext(self):
        return AbstractBlock.isnext(self)
    def parse_ruler(self,ruler):
        """Parse ruler calculating underline and ruler column widths."""
        fc = re.escape(self.fillchar)
        # Strip and save optional tablewidth from end of ruler.
        mo = re.match(r'^(.*'+fc+r'+)([\d\.]+)$',ruler)
        if mo:
            ruler = mo.group(1)
            self.tablewidth = float(mo.group(2))
            self.attributes['tablewidth'] = str(float(self.tablewidth))
        else:
            self.tablewidth = None
            self.attributes['tablewidth'] = '100.0'
        # Guess whether column widths are specified numerically or not.
        if ruler[1] != self.fillchar:
            # If the first column does not start with a fillchar then numeric.
            self.isnumeric = True
        elif ruler[1:] == self.fillchar*len(ruler[1:]):
            # The case of one column followed by fillchars is numeric.
            self.isnumeric = True
        else:
            self.isnumeric = False
        # Underlines must be 3 or more fillchars.
        self.underline = r'^' + fc + r'{3,}$'
        splits = re.split(self.COL_STOP,ruler)[1:]
        # Build self.columns.
        for i in range(0,len(splits),2):
            c = Column()
            c.colalign = self.ALIGNMENTS[splits[i]]
            s = splits[i+1]
            if self.isnumeric:
                # Strip trailing fillchars.
                s = re.sub(fc+r'+$','',s)
                if s == '':
                    c.rulerwidth = None
                else:
                    c.rulerwidth = int(validate(s,'int($)>0',
                        'malformed ruler: bad width'))
            else:   # Calculate column width from inter-fillchar intervals.
                if not re.match(r'^'+fc+r'+$',s):
                    raise EAsciiDoc,'malformed ruler: illegal fillchars'
                c.rulerwidth = len(s)+1
            self.columns.append(c)
        # Fill in unspecified ruler widths.
        if self.isnumeric:
            if self.columns[0].rulerwidth is None:
                prevwidth = 1
            for c in self.columns:
                if c.rulerwidth is None:
                    c.rulerwidth = prevwidth
                prevwidth = c.rulerwidth
    def build_colspecs(self):
        """Generate colwidths and colspecs. This can only be done after the
        table arguments have been parsed since we use the table format."""
        self.attributes['cols'] = len(self.columns)
        # Calculate total ruler width.
        totalwidth = 0
        for c in self.columns:
            totalwidth = totalwidth + c.rulerwidth
        if totalwidth <= 0:
            raise EAsciiDoc,'zero width table'
        # Calculate marked up colwidths from rulerwidths.
        for c in self.columns:
            # Convert ruler width to output page width.
            width = float(c.rulerwidth)
            if self.format == 'fixed':
                if self.tablewidth is None:
                    # Size proportional to ruler width.
                    colfraction = width/config.textwidth
                else:
                    # Size proportional to page width.
                    colfraction = width/totalwidth
            else:
                    # Size proportional to page width.
                colfraction = width/totalwidth
            c.colwidth = colfraction * config.pagewidth # To page units.
            if self.tablewidth is not None:
                c.colwidth = c.colwidth * self.tablewidth   # Scale factor.
                if self.tablewidth > 1:
                    c.colwidth = c.colwidth/100 # tablewidth is in percent.
        # Build colspecs.
        if self.colspec:
            cols = []
            i = 0
            for c in self.columns:
                i += 1
                self.attributes['colalign'] = c.colalign
                self.attributes['colwidth'] = str(int(c.colwidth))
                self.attributes['colnumber'] = str(i + 1)
                s = subs_attrs(self.colspec,self.attributes)
                if not s:
                    warning('colspec dropped: contains undefined attribute')
                else:
                    cols.append(s)
            self.attributes['colspecs'] = writer.newline.join(cols)
    def split_rows(self,rows):
        """Return a two item tuple containing a list of lines up to but not
        including the next underline (continued lines are joined ) and the
        tuple of all lines after the underline."""
        reo = re.compile(self.underline)
        i = 0
        while not reo.match(rows[i]):
            i = i+1
        if i == 0:
            raise EAsciiDoc,'missing table rows'
        if i >= len(rows):
            raise EAsciiDoc,'closing [%s] underline expected' % self.name
        return (join_lines(rows[:i]), rows[i+1:])
    def parse_rows(self, rows, rtag, dtag):
        """Parse rows list using the row and data tags. Returns a substituted
        list of output lines."""
        result = []
        # Source rows are parsed as single block, rather than line by line, to
        # allow the CSV reader to handle multi-line rows.
        if self.format == 'fixed':
            rows = self.parse_fixed(rows)
        elif self.format == 'csv':
            rows = self.parse_csv(rows)
        elif self.format == 'dsv':
            rows = self.parse_dsv(rows)
        else:
            assert True,'illegal table format'
        # Substitute and indent all data in all rows.
        stag,etag = subs_tag(rtag,self.attributes)
        for row in rows:
            result.append('  '+stag)
            for data in self.subs_row(row,dtag):
                result.append('    '+data)
            result.append('  '+etag)
        return result
    def subs_row(self, data, dtag):
        """Substitute the list of source row data elements using the data tag.
        Returns a substituted list of output table data items."""
        result = []
        if len(data) < len(self.columns):
            warning('fewer row data items then table columns')
        if len(data) > len(self.columns):
            warning('more row data items than table columns')
        for i in range(len(self.columns)):
            if i > len(data) - 1:
                d = ''  # Fill missing column data with blanks.
            else:
                d = data[i]
            c = self.columns[i]
            self.attributes['colalign'] = c.colalign
            self.attributes['colwidth'] = str(int(c.colwidth))
            self.attributes['colnumber'] = str(i + 1)
            stag,etag = subs_tag(dtag,self.attributes)
            # Insert AsciiDoc line break (' +') where row data has newlines
            # ('\n').  This is really only useful when the table format is csv
            # and the output markup is HTML. It's also a bit dubious in that it
            # assumes the user has not modified the shipped line break pattern.
            subs = self.get_subs()[0]
            if 'replacements' in subs:
                # Insert line breaks in cell data.
                d = re.sub(r'(?m)\n',r' +\n',d)
                d = d.split('\n')    # So writer.newline is written.
            else:
                d = [d]
            result = result + [stag] + Lex.subs(d,subs) + [etag]
        return result
    def parse_fixed(self,rows):
        """Parse the list of source table rows. Each row item in the returned
        list contains a list of cell data elements."""
        result = []
        for row in rows:
            data = []
            start = 0
            # build an encoded representation
            row = char_decode(row)
            for c in self.columns:
                end = start + c.rulerwidth
                if c is self.columns[-1]:
                    # Text in last column can continue forever.
                    # Use the encoded string to slice, but convert back
                    # to plain string before further processing
                    data.append(char_encode(row[start:]).strip())
                else:
                    data.append(char_encode(row[start:end]).strip())
                start = end
            result.append(data)
        return result
    def parse_csv(self,rows):
        """Parse the list of source table rows. Each row item in the returned
        list contains a list of cell data elements."""
        import StringIO
        import csv
        result = []
        rdr = csv.reader(StringIO.StringIO('\r\n'.join(rows)),
            skipinitialspace=True)
        try:
            for row in rdr:
                result.append(row)
        except:
            raise EAsciiDoc,'csv parse error: %s' % row
        return result
    def parse_dsv(self,rows):
        """Parse the list of source table rows. Each row item in the returned
        list contains a list of cell data elements."""
        separator = self.attributes.get('separator',':')
        separator = eval('"'+separator+'"')
        if len(separator) != 1:
            raise EAsciiDoc,'malformed dsv separator: %s' % separator
        # TODO If separator is preceeded by an odd number of backslashes then
        # it is escaped and should not delimit.
        result = []
        for row in rows:
            # Skip blank lines
            if row == '': continue
            # Unescape escaped characters.
            row = eval('"'+row.replace('"','\\"')+'"')
            data = row.split(separator)
            data = [s.strip() for s in data]
            result.append(data)
        return result
    def translate(self):
        AbstractBlock.translate(self)
        # Reset instance specific properties.
        self.underline = None
        self.columns = []
        attrs = {}
        BlockTitle.consume(attrs)
        # Add relevant globals to table substitutions.
        attrs['pagewidth'] = str(config.pagewidth)
        attrs['pageunits'] = config.pageunits
        # Mix in document attribute list.
        AttributeList.consume(attrs)
        # Validate overridable attributes.
        for k,v in attrs.items():
            if k == 'format':
                if v not in self.FORMATS:
                    raise EAsciiDoc, 'illegal [%s] %s: %s' % (self.name,k,v)
                self.format = v
            elif k == 'tablewidth':
                try:
                    self.tablewidth = float(attrs['tablewidth'])
                except:
                    raise EAsciiDoc, 'illegal [%s] %s: %s' % (self.name,k,v)
        self.merge_attributes(attrs)
        # Parse table ruler.
        ruler = reader.read()
        assert re.match(self.delimiter,ruler)
        self.parse_ruler(ruler)
        # Read the entire table.
        table = []
        while True:
            line = reader.read_next()
            # Table terminated by underline followed by a blank line or EOF.
            if len(table) > 0 and re.match(self.underline,table[-1]):
                if line in ('',None):
                    break;
            if line is None:
                raise EAsciiDoc,'closing [%s] underline expected' % self.name
            table.append(reader.read())
        # EXPERIMENTAL: The number of lines in the table, requested by Benjamin Klum.
        self.attributes['rows'] = str(len(table))
        #TODO: Inherited validate() doesn't set check_msg, needs checking.
        if self.check_msg:  # Skip if table definition was marked invalid.
            warning('skipping %s table: %s' % (self.name,self.check_msg))
            return
        # Generate colwidths and colspecs.
        self.build_colspecs()
        # Generate headrows, footrows, bodyrows.
        # Headrow, footrow and bodyrow data replaces same named attributes in
        # the table markup template. In order to ensure this data does not get
        # a second attribute substitution (which would interfere with any
        # already substituted inline passthroughs) unique placeholders are used
        # (the tab character does not appear elsewhere since it is expanded on
        # input) which are replaced after template attribute substitution.
        headrows = footrows = []
        bodyrows,table = self.split_rows(table)
        if table:
            headrows = bodyrows
            bodyrows,table = self.split_rows(table)
            if table:
                footrows,table = self.split_rows(table)
        if headrows:
            headrows = self.parse_rows(headrows, self.headrow, self.headdata)
            headrows = writer.newline.join(headrows)
            self.attributes['headrows'] = '\theadrows\t'
        if footrows:
            footrows = self.parse_rows(footrows, self.footrow, self.footdata)
            footrows = writer.newline.join(footrows)
            self.attributes['footrows'] = '\tfootrows\t'
        bodyrows = self.parse_rows(bodyrows, self.bodyrow, self.bodydata)
        bodyrows = writer.newline.join(bodyrows)
        self.attributes['bodyrows'] = '\tbodyrows\t'
        table = subs_attrs(config.sections[self.template],self.attributes)
        table = writer.newline.join(table)
        # Before we finish replace the table head, foot and body place holders
        # with the real data.
        if headrows:
            table = table.replace('\theadrows\t', headrows, 1)
        if footrows:
            table = table.replace('\tfootrows\t', footrows, 1)
        table = table.replace('\tbodyrows\t', bodyrows, 1)
        writer.write(table)

class Tables(AbstractBlocks):
    """List of tables."""
    BLOCK_TYPE = Table
    PREFIX = 'tabledef-'
    def __init__(self):
        AbstractBlocks.__init__(self)
    def load(self,sections):
        AbstractBlocks.load(self,sections)
        """Update tables defined in 'sections' dictionary."""
    def validate(self):
        # Does not call AbstractBlocks.validate().
        # Check we have a default table definition,
        for i in range(len(self.blocks)):
            if self.blocks[i].name == 'tabledef-default':
                default = self.blocks[i]
                break
        else:
            raise EAsciiDoc,'missing [table-default] section'
        # Set default table defaults.
        if default.format is None: default.subs = 'fixed'
        # Propagate defaults to unspecified table parameters.
        for b in self.blocks:
            if b is not default:
                if b.fillchar is None: b.fillchar = default.fillchar
                if b.format is None: b.format = default.format
                if b.template is None: b.template = default.template
                if b.colspec is None: b.colspec = default.colspec
                if b.headrow is None: b.headrow = default.headrow
                if b.footrow is None: b.footrow = default.footrow
                if b.bodyrow is None: b.bodyrow = default.bodyrow
                if b.headdata is None: b.headdata = default.headdata
                if b.footdata is None: b.footdata = default.footdata
                if b.bodydata is None: b.bodydata = default.bodydata
        # Check all tables have valid fill character.
        for b in self.blocks:
            if not b.fillchar or len(b.fillchar) != 1:
                raise EAsciiDoc,'[%s] missing or illegal fillchar' % b.name
        # Build combined tables delimiter patterns and assign defaults.
        delimiters = []
        for b in self.blocks:
            # Ruler is:
            #   (ColStop,(ColWidth,FillChar+)?)+, FillChar+, TableWidth?
            b.delimiter = r'^(' + Table.COL_STOP \
                + r'(\d*|' + re.escape(b.fillchar) + r'*)' \
                + r')+' \
                + re.escape(b.fillchar) + r'+' \
                + '([\d\.]*)$'
            delimiters.append(b.delimiter)
            if not b.headrow:
                b.headrow = b.bodyrow
            if not b.footrow:
                b.footrow = b.bodyrow
            if not b.headdata:
                b.headdata = b.bodydata
            if not b.footdata:
                b.footdata = b.bodydata
        self.delimiter = join_regexp(delimiters)
        # Check table definitions are valid.
        for b in self.blocks:
            b.validate()
            if config.verbose:
                if b.check_msg:
                    warning('[%s] table definition: %s' % (b.name,b.check_msg))

class Macros:
    # Default system macro syntax.
    SYS_DEFAULT = r'(?u)^(?P<name>\w(\w|-)*?)::(?P<target>\S*?)' + \
                  r'(\[(?P<attrlist>.*?)\])$'
    def __init__(self):
        self.macros = []        # List of Macros.
        self.current = None     # The last matched block macro.
        # Initialize default system macro.
        m = Macro()
        m.pattern = self.SYS_DEFAULT
        m.prefix = '+'
        m.reo = re.compile(m.pattern)
        self.macros.append(m)
    def load(self,entries):
        for entry in entries:
            m = Macro()
            m.load(entry)
            if m.name is None:
                # Delete undefined macro.
                for i in range(len(self.macros)-1,-1,-1):
                    if self.macros[i].pattern == m.pattern:
                        del self.macros[i]
            else:
                # Check for duplicates.
                for m2 in self.macros:
                    if m.equals(m2):
                        verbose('macro redefinition: %s%s' % (m.prefix,m.name))
                        break
                else:
                    self.macros.append(m)
    def dump(self):
        write = lambda s: sys.stdout.write('%s%s' % (s,writer.newline))
        write('[macros]')
        # Dump all macros except the first (built-in system) macro.
        for m in self.macros[1:]:
            write('%s=%s%s' % (m.pattern,m.prefix,m.name))
        write('')
    def validate(self):
        # Check all named sections exist.
        if config.verbose:
            for m in self.macros:
                if m.name and m.prefix != '+':
                    m.section_name()
    def subs(self,text,prefix='',callouts=False):
        # If callouts is True then only callout macros are processed, if False
        # then all non-callout macros are processed.
        result = text
        for m in self.macros:
            if m.prefix == prefix:
                if callouts ^ (m.name != 'callout'):
                    result = m.subs(result)
        return result
    def isnext(self):
        """Return matching macro if block macro is next on reader."""
        reader.skip_blank_lines()
        line = reader.read_next()
        if line:
            for m in self.macros:
                if m.prefix == '#':
                    if m.reo.match(line):
                        self.current = m
                        return m
        return False
    def match(self,prefix,name,text):
        """Return re match object matching 'text' with macro type 'prefix',
        macro name 'name'."""
        for m in self.macros:
            if m.prefix == prefix:
                mo = m.reo.match(text)
                if mo:
                    if m.name == name:
                        return mo
                    if re.match(name,mo.group('name')):
                        return mo
        return None

# Macro set just prior to calling _subs_macro(). Ugly but there's no way
# to pass optional arguments with _subs_macro().
_macro = None

def _subs_macro(mo):
    """Function called to perform inline macro substitution. Uses matched macro
    regular expression object and returns string containing the substituted
    macro body. Called by Macros().subs()."""
    # Check if macro reference is escaped.
    if mo.group()[0] == '\\':
        return mo.group()[1:]   # Strip leading backslash.
    d = mo.groupdict()
    # Delete groups that didn't participate in match.
    for k,v in d.items():
        if v is None: del d[k]
    if _macro.name:
        name = _macro.name
    else:
        if not d.has_key('name'):
            warning('missing macro name group: %s' % mo.re.pattern)
            return ''
        name = d['name']
    section_name = _macro.section_name(name)
    if not section_name:
        return ''
    # If we're dealing with a block macro get optional block ID and block title.
    if _macro.prefix == '#':
        AttributeList.consume(d)
        BlockTitle.consume(d)
    # Parse macro attributes.
    if d.has_key('attrlist'):
        if d['attrlist'] in (None,''):
            del d['attrlist']
        else:
            parse_attributes(d['attrlist'],d)
    if name == 'callout':
        listindex =int(d['index'])
        d['coid'] = calloutmap.add(listindex)
    # Unescape special characters in LaTeX target file names.
    if document.backend == 'latex' and d.has_key('target') and d['target']:
        if not d.has_key('0'):
            d['0'] = d['target']
        d['target']= config.subs_specialchars_reverse(d['target'])
    # BUG: We've already done attribute substitution on the macro which means
    # that any escaped attribute references are now unescaped and will be
    # substituted by config.subs_section() below. As a partial fix have withheld
    # {0} from substitution but this kludge doesn't fix it for other attributes
    # containing unescaped references.
    a0 = d.get('0')
    if a0:
        d['0'] = chr(0)  # Replace temporarily with unused character.
    body = config.subs_section(section_name,d)
    if len(body) == 0:
        result = ''
    elif len(body) == 1:
        result = body[0]
    else:
        if _macro.prefix == '#':
            result = writer.newline.join(body)
        else:
            # Internally processed inline macros use UNIX line separator.
            result = '\n'.join(body)
    if a0:
        result = result.replace(chr(0), a0)
    return result

class Macro:
    def __init__(self):
        self.pattern = None     # Matching regular expression.
        self.name = ''          # Conf file macro name (None if implicit).
        self.prefix = ''        # '' if inline, '+' if system, '#' if block.
        self.reo = None         # Compiled pattern re object.
    def section_name(self,name=None):
        """Return macro markup template section name based on macro name and
        prefix.  Return None section not found."""
        assert self.prefix != '+'
        if not name:
            assert self.name
            name = self.name
        if self.prefix == '#':
            suffix = '-blockmacro'
        else:
            suffix = '-inlinemacro'
        if config.sections.has_key(name+suffix):
            return name+suffix
        else:
            warning('missing macro section: [%s]' % name+suffix)
            return None
    def equals(self,m):
        if self.pattern != m.pattern:
            return False
        if self.name != m.name:
            return False
        if self.prefix != m.prefix:
            return False
        return True
    def load(self,entry):
        e = parse_entry(entry)
        if not e:
            raise EAsciiDoc,'malformed macro entry: %s' % entry
        if not is_regexp(e[0]):
            raise EAsciiDoc,'illegal %s macro regular expression: %s' \
                % (e[1],e[0])
        self.pattern, self.name = e
        self.reo = re.compile(self.pattern)
        if self.name:
            if self.name[0] in ('+','#'):
                self.prefix, self.name = self.name[0], self.name[1:]
        if self.name and not is_name(self.name):
            raise EAsciiDoc,'illegal section name in macro entry: %s' % entry
    def subs(self,text):
        global _macro
        _macro = self           # Pass the macro to _subs_macro().
        return self.reo.sub(_subs_macro,text)
    def translate(self):
        """ Block macro translation."""
        assert self.prefix == '#'
        s = reader.read()
        s = subs_attrs(s)       # Substitute global attributes.
        if s:
            s = self.subs(s)
            if s:
                writer.write(s)

class CalloutMap:
    def __init__(self):
        self.comap = {}         # key = list index, value = callouts list.
        self.calloutindex = 0   # Current callout index number.
        self.listnumber = 1     # Current callout list number.
    def listclose(self):
        # Called when callout list is closed.
        self.listnumber += 1
        self.calloutindex = 0
        self.comap = {}
    def add(self,listindex):
        # Add next callout index to listindex map entry. Return the callout id.
        self.calloutindex += 1
        # Append the coindex to a list in the comap dictionary.
        if not self.comap.has_key(listindex):
            self.comap[listindex] = [self.calloutindex]
        else:
            self.comap[listindex].append(self.calloutindex)
        return self.calloutid(self.listnumber, self.calloutindex)
    def calloutid(listnumber,calloutindex):
        return 'CO%d-%d' % (listnumber,calloutindex)
    calloutid = staticmethod(calloutid)
    def calloutids(self,listindex):
        # Retieve list of callout indexes that refer to listindex.
        if self.comap.has_key(listindex):
            result = ''
            for coindex in self.comap[listindex]:
                result += ' ' + self.calloutid(self.listnumber,coindex)
            return result.strip()
        else:
            error('no callouts refer to list item '+str(listindex))
            return ''
    def validate(self,maxlistindex):
        # Check that all list indexes referenced by callouts exist.
        for listindex in self.comap.keys():
            if listindex > maxlistindex:
                warning('callout refers to non-existent list item '
                        + str(listindex))

#---------------------------------------------------------------------------
# Input stream Reader and output stream writer classes.
#---------------------------------------------------------------------------

class Reader1:
    """Line oriented AsciiDoc input file reader. Processes include and
    conditional inclusion system macros. Tabs are expanded and lines are right
    trimmed."""
    # This class is not used directly, use Reader class instead.
    READ_BUFFER_MIN = 10            # Read buffer low level.
    def __init__(self):
        self.f = None           # Input file object.
        self.fname = None       # Input file name.
        self.next = []          # Read ahead buffer containing
                                # [filename,linenumber,linetext] lists.
        self.cursor = None      # Last read() [filename,linenumber,linetext].
        self.tabsize = 8        # Tab expansion number of spaces.
        self.parent = None      # Included reader's parent reader.
        self._lineno = 0        # The last line read from file object f.
        self.include_depth = 0  # Current include depth.
        self.include_max = 5    # Maxiumum allowed include depth.
    def open(self,fname):
        self.fname = fname
        verbose('reading: '+fname)
        if fname == '<stdin>':
            self.f = sys.stdin
        else:
            self.f = open(fname,'rb')
        self._lineno = 0            # The last line read from file object f.
        self.next = []
        # Prefill buffer by reading the first line and then pushing it back.
        if Reader1.read(self):
            self.unread(self.cursor)
            self.cursor = None
    def closefile(self):
        """Used by class methods to close nested include files."""
        self.f.close()
        self.next = []
    def close(self):
        self.closefile()
        self.__init__()
    def read(self, skip=False):
        """Read next line. Return None if EOF. Expand tabs. Strip trailing
        white space. Maintain self.next read ahead buffer. If skip=True then
        conditional exclusion is active (ifdef and ifndef macros)."""
        # Top up buffer.
        if len(self.next) <= self.READ_BUFFER_MIN:
            s = self.f.readline()
            if s:
                self._lineno = self._lineno + 1
            while s:
                if self.tabsize != 0:
                    s = s.expandtabs(self.tabsize)
                s = s.rstrip()
                self.next.append([self.fname,self._lineno,s])
                if len(self.next) > self.READ_BUFFER_MIN:
                    break
                s = self.f.readline()
                if s:
                    self._lineno = self._lineno + 1
        # Return first (oldest) buffer entry.
        if len(self.next) > 0:
            self.cursor = self.next[0]
            del self.next[0]
            result = self.cursor[2]
            # Check for include macro.
            mo = macros.match('+',r'include[1]?',result)
            if mo and not skip:
                # Perform attribute substitution on inlcude macro file name.
                fname = subs_attrs(mo.group('target'))
                if not fname:
                    return Reader1.read(self)   # Return next input line.
                if self.include_depth >= self.include_max:
                    raise EAsciiDoc,'maxiumum inlcude depth exceeded'
                if self.fname != '<stdin>':
                    fname = os.path.expandvars(os.path.expanduser(fname))
                    fname = safe_filename(fname, os.path.dirname(self.fname))
                    if not fname:
                        return Reader1.read(self)   # Return next input line.
                    if mo.group('name') == 'include1':
                        if not config.dumping:
                            # Store the include file in memory for later
                            # retrieval by the {include1:} system attribute.
                            config.include1[fname] = \
                                [s.rstrip() for s in open(fname)]
                            return '{include1:%s}' % fname
                        else:
                            # This is a configuration dump, just pass the macro
                            # call through.
                            return result
                # Parse include macro attributes.
                attrs = {}
                parse_attributes(mo.group('attrlist'),attrs)
                # Clone self and set as parent (self assumes the role of child).
                parent = Reader1()
                assign(parent,self)
                self.parent = parent
                if attrs.has_key('tabsize'):
                    self.tabsize = int(validate(attrs['tabsize'],'int($)>=0', \
                        'illegal include macro tabsize argument'))
                self.open(fname)
                self.include_depth = self.include_depth + 1
                result = Reader1.read(self)
        else:
            if not Reader1.eof(self):
                result = Reader1.read(self)
            else:
                result = None
        return result
    def eof(self):
        """Returns True if all lines have been read."""
        if len(self.next) == 0:
            # End of current file.
            if self.parent:
                self.closefile()
                assign(self,self.parent)    # Restore parent reader.
                return Reader1.eof(self)
            else:
                return True
        else:
            return False
    def read_next(self):
        """Like read() but does not advance file pointer."""
        if Reader1.eof(self):
            return None
        else:
            return self.next[0][2]
    def unread(self,cursor):
        """Push the line (filename,linenumber,linetext) tuple back into the read
        buffer. Note that it's up to the caller to restore the previous
        cursor."""
        assert cursor
        self.next.insert(0,cursor)

class Reader(Reader1):
    """ Wraps (well, sought of) Reader1 class and implements conditional text
    inclusion."""
    def __init__(self):
        Reader1.__init__(self)
        self.depth = 0          # if nesting depth.
        self.skip = False       # true if we're skipping ifdef...endif.
        self.skipname = ''      # Name of current endif macro target.
        self.skipto = -1        # The depth at which skipping is reenabled.
    def read_super(self):
        result = Reader1.read(self,self.skip)
        if result is None and self.skip:
            raise EAsciiDoc,'missing endif::%s[]' % self.skipname
        return result
    def read(self):
        result = self.read_super()
        if result is None:
            return None
        while self.skip:
            mo = macros.match('+',r'ifdef|ifndef|endif',result)
            if mo:
                name = mo.group('name')
                target = mo.group('target')
                if name == 'endif':
                    self.depth = self.depth-1
                    if self.depth < 0:
                        raise EAsciiDoc,'mismatched macro: %s' % result
                    if self.depth == self.skipto:
                        self.skip = False
                        if target and self.skipname != target:
                            raise EAsciiDoc,'mismatched macro: %s' % result
                else:   # ifdef or ifndef.
                    if not target:
                        raise EAsciiDoc,'missing macro target: %s' % result
                    self.depth = self.depth+1
            result = self.read_super()
            if result is None:
                return None
        mo = macros.match('+',r'ifdef|ifndef|endif',result)
        if mo:
            name = mo.group('name')
            target = mo.group('target')
            if name == 'endif':
                self.depth = self.depth-1
            else:   # ifdef or ifndef.
                if not target:
                    raise EAsciiDoc,'missing macro target: %s' % result
                defined = document.attributes.get(target) is not None
                if name == 'ifdef':
                    self.skip = not defined
                else:   # ifndef.
                    self.skip = defined
                if self.skip:
                    self.skipto = self.depth
                    self.skipname = target
                self.depth = self.depth+1
            result = self.read()
        if result:
            # Expand executable block macros.
            mo = macros.match('+',r'eval|sys|sys2',result)
            if mo:
                action = mo.group('name')
                cmd = mo.group('attrlist')
                s = system(action, cmd, is_macro=True)
                if s is not None:
                    self.cursor[2] = s  # So we don't re-evaluate.
                    result = s
        return result
    def eof(self):
        return self.read_next() is None
    def read_next(self):
        save_cursor = self.cursor
        result = self.read()
        if result is not None:
            self.unread(self.cursor)
            self.cursor = save_cursor
        return result
    def read_all(self,fname):
        """Read all lines from file fname and return as list. Use like class
        method: Reader().read_all(fname)"""
        result = []
        self.open(fname)
        try:
            while not self.eof():
                result.append(self.read())
        finally:
            self.close()
        return result
    def read_lines(self,count=1):
        """Return tuple containing count lines."""
        result = []
        i = 0
        while i < count and not self.eof():
            result.append(self.read())
        return tuple(result)
    def read_ahead(self,count=1):
        """Same as read_lines() but does not advance the file pointer."""
        result = []
        putback = []
        save_cursor = self.cursor
        try:
            i = 0
            while i < count and not self.eof():
                result.append(self.read())
                putback.append(self.cursor)
                i = i+1
            while putback:
                self.unread(putback.pop())
        finally:
            self.cursor = save_cursor
        return tuple(result)
    def skip_blank_lines(self):
        reader.read_until(r'\s*\S+')
    def read_until(self,pattern,same_file=False):
        """Like read() but reads lines up to (but not including) the first line
        that matches the pattern regular expression. If same_file is True
        then the terminating pattern must occur in the file the was being read
        when the routine was called."""
        if same_file:
            fname = self.cursor[0]
        result = []
        reo = re.compile(pattern)
        while not self.eof():
            save_cursor = self.cursor
            s = self.read()
            if (not same_file or fname == self.cursor[0]) and reo.match(s):
                self.unread(self.cursor)
                self.cursor = save_cursor
                break
            result.append(s)
        return tuple(result)
    # NOT USED -- part of unimplemented attempt a generalised line continuation.
    def read_continuation(self):
        """Like read() but treats trailing backslash as line continuation
        character."""
        s = self.read()
        if s is None:
            return None
        result = ''
        while s is not None and len(s) > 0 and s[-1] == '\\':
            result = result + s[:-1]
            s = self.read()
        if s is not None:
            result = result + s
        return result
    # NOT USED -- part of unimplemented attempt a generalised line continuation.
    def read_next_continuation(self):
        """Like read_next() but treats trailing backslash as line continuation
        character."""
        save_cursor = self.cursor
        result = self.read_continuation()
        if result is not None:
            self.unread(self.cursor)
            self.cursor = save_cursor
        return result

class Writer:
    """Writes lines to output file."""
    newline = '\r\n'            # End of line terminator.
    f = None                    # Output file object.
    fname= None                 # Output file name.
    lines_out = 0               # Number of lines written.
    skip_blank_lines = False    # If True don't output blank lines.
    def open(self,fname):
        self.fname = os.path.abspath(fname)
        verbose('writing: '+fname)
        if fname == '<stdout>':
            self.f = sys.stdout
        else:
            self.f = open(fname,'wb+')
        self.lines_out = 0
    def close(self):
        if self.fname != '<stdout>':
            self.f.close()
    def write_line(self, line=None):
        if not (self.skip_blank_lines and (not line or not line.strip())):
            if line is not None:
                self.f.write(line + self.newline)
            else:
                self.f.write(self.newline)
            self.lines_out = self.lines_out + 1
    def write(self,*args):
        """Iterates arguments, writes tuple and list arguments one line per
        element, else writes argument as single line. If no arguments writes
        blank line. If argument is None nothing is written. self.newline is
        appended to each line."""
        if len(args) == 0:
            self.write_line()
            self.lines_out = self.lines_out + 1
        else:
            for arg in args:
                if isinstance(arg,list) or isinstance(arg,tuple):
                    for s in arg:
                        self.write_line(s)
                elif arg is not None:
                    self.write_line(arg)
    def write_tag(self,tagname,content,subs=None,d=None):
        """Write content enveloped by configuration file tag tagname.
        Substitutions specified in the 'subs' list are perform on the
        'content'."""
        if subs is None:
            subs = config.subsnormal
        stag,etag = config.tag(tagname,d)
        if stag:
            self.write(stag)
        if content:
            self.write(Lex.subs(content,subs))
        if etag:
            self.write(etag)

#---------------------------------------------------------------------------
# Configuration file processing.
#---------------------------------------------------------------------------
def _subs_specialwords(mo):
    """Special word substitution function called by
    Config.subs_specialwords()."""
    word = mo.re.pattern                    # The special word.
    template = config.specialwords[word]    # The corresponding markup template.
    if not config.sections.has_key(template):
        raise EAsciiDoc,'missing special word template [%s]' % template
    if mo.group()[0] == '\\':
        return mo.group()[1:]   # Return escaped word.
    args = {}
    args['words'] = mo.group()  # The full match string is argument 'words'.
    args.update(mo.groupdict()) # Add other named match groups to the arguments.
    # Delete groups that didn't participate in match.
    for k,v in args.items():
        if v is None: del args[k]
    lines = subs_attrs(config.sections[template],args)
    if len(lines) == 0:
        result = ''
    elif len(lines) == 1:
        result = lines[0]
    else:
        result = writer.newline.join(lines)
    return result

class Config:
    """Methods to process configuration files."""
    # Predefined section name regexp's.
    SPECIAL_SECTIONS= ('tags','miscellaneous','attributes','specialcharacters',
            'specialwords','macros','replacements','quotes','titles',
            r'paradef.+',r'listdef.+',r'blockdef.+',r'tabledef.*',
            'replacements2')
    def __init__(self):
        self.sections = OrderedDict()   # Keyed by section name containing
                                        # lists of section lines.
        # Command-line options.
        self.verbose = False
        self.header_footer = True       # -s, --no-header-footer option.
        # [miscellaneous] section.
        self.tabsize = 8
        self.textwidth = 70
        self.newline = '\r\n'
        self.pagewidth = None
        self.pageunits = None
        self.outfilesuffix = ''
        self.subsnormal = SUBS_NORMAL
        self.subsverbatim = SUBS_VERBATIM

        self.tags = {}          # Values contain (stag,etag) tuples.
        self.specialchars = {}  # Values of special character substitutions.
        self.specialwords = {}  # Name is special word pattern, value is macro.
        self.replacements = OrderedDict()   # Key is find pattern, value is
                                            #replace pattern.
        self.replacements2 = OrderedDict()
        self.specialsections = {} # Name is special section name pattern, value
                                  # is corresponding section name.
        self.quotes = {}        # Values contain corresponding tag name.
        self.fname = ''         # Most recently loaded configuration file name.
        self.conf_attrs = {}    # Glossary entries from conf files.
        self.cmd_attrs = {}     # Attributes from command-line -a options.
        self.loaded = []        # Loaded conf files.
        self.include1 = {}      # Holds include1::[] files for {include1:}.
        self.dumping = False    # True if asciidoc -c option specified.

    def load(self,fname,dir=None):
        """Loads sections dictionary with sections from file fname.
        Existing sections are overlaid. Silently skips missing configuration
        files."""
        if dir:
            fname = os.path.join(dir, fname)
        # Sliently skip missing configuration file.
        if not os.path.isfile(fname):
            return
        # Don't load conf files twice (local and application conf files are the
        # same if the source file is in the application directory).
        if os.path.realpath(fname) in self.loaded:
            return
        rdr = Reader()  # Reader processes system macros.
        rdr.open(fname)
        self.fname = fname
        reo = re.compile(r'(?u)^\[(?P<section>[^\W\d][\w-]*)\]\s*$')
        sections = OrderedDict()
        section,contents = '',[]
        while not rdr.eof():
            s = rdr.read()
            if s and s[0] == '#':       # Skip comment lines.
                continue
            if s[:2] == '\\#':          # Unescape lines starting with '#'.
                s = s[1:]
            s = s.rstrip()
            found = reo.findall(s)
            if found:
                if section:             # Store previous section.
                    if sections.has_key(section) \
                        and self.is_special_section(section):
                        if ''.join(contents):
                            # Merge special sections.
                            sections[section] = sections[section] + contents
                        else:
                            print 'blank section'
                            del sections[section]
                    else:
                        sections[section] = contents
                section = found[0].lower()
                contents = []
            else:
                contents.append(s)
        if section and contents:        # Store last section.
            if sections.has_key(section) \
                and self.is_special_section(section):
                if ''.join(contents):
                    # Merge special sections.
                    sections[section] = sections[section] + contents
                else:
                    del sections[section]
            else:
                sections[section] = contents
        rdr.close()
        # Delete blank lines from sections.
        for k in sections.keys():
            for i in range(len(sections[k])-1,-1,-1):
                if not sections[k][i]:
                    del sections[k][i]
                elif not self.is_special_section(k):
                    break   # Only trailing blanks from non-special sections.
        # Add/overwrite new sections.
        self.sections.update(sections)
        self.parse_tags()
        # Internally [miscellaneous] section entries are just attributes.
        d = {}
        parse_entries(sections.get('miscellaneous',()), d, unquote=True,
                allow_name_only=True)
        update_attrs(self.conf_attrs,d)
        d = {}
        parse_entries(sections.get('attributes',()), d, unquote=True,
                allow_name_only=True)
        update_attrs(self.conf_attrs,d)
        # Update document attributes so they are available immediately.
        document.init_attrs()
        d = {}
        parse_entries(sections.get('titles',()),d)
        Title.load(d)
        parse_entries(sections.get('specialcharacters',()),self.specialchars,escape_delimiter=False)
        parse_entries(sections.get('quotes',()),self.quotes)
        self.parse_specialwords()
        self.parse_replacements()
        self.parse_replacements('replacements2')
        self.parse_specialsections()
        paragraphs.load(sections)
        lists.load(sections)
        blocks.load(sections)
        tables.load(sections)
        macros.load(sections.get('macros',()))
        self.loaded.append(os.path.realpath(fname))

    def load_all(self,dir):
        """Load the standard configuration files from directory 'dir'."""
        self.load('asciidoc.conf',dir)
        conf = document.backend + '.conf'
        self.load(conf,dir)
        conf = document.backend + '-' + document.doctype + '.conf'
        self.load(conf,dir)
        lang = document.attributes.get('lang')
        if lang:
            conf = 'lang-' + lang + '.conf'
            self.load(conf,dir)
        # Load ./filters/*.conf files if they exist.
        filters = os.path.join(dir,'filters')
        if os.path.isdir(filters):
            for f in os.listdir(filters):
                if re.match(r'^.+\.conf$',f):
                    self.load(f,filters)

    def load_miscellaneous(self,d):
        """Set miscellaneous configuration entries from dictionary 'd'."""
        def set_misc(name,rule='True',intval=False):
            if d.has_key(name):
                errmsg = 'illegal [miscellaneous] %s entry' % name
                if intval:
                    setattr(self, name, int(validate(d[name],rule,errmsg)))
                else:
                    setattr(self, name, validate(d[name],rule,errmsg))
        set_misc('tabsize','int($)>0',intval=True)
        set_misc('textwidth','int($)>0',intval=True)
        set_misc('pagewidth','int($)>0',intval=True)
        set_misc('pageunits')
        set_misc('outfilesuffix')
        if d.has_key('newline'):
            # Convert escape sequences to their character values.
            self.newline = eval('"'+d['newline']+'"')
        if d.has_key('subsnormal'):
            self.subsnormal = parse_options(d['subsnormal'],SUBS_OPTIONS,
                    'illegal [%s] %s: %s' %
                    ('miscellaneous','subsnormal',d['subsnormal']))
        if d.has_key('subsverbatim'):
            self.subsverbatim = parse_options(d['subsverbatim'],SUBS_OPTIONS,
                    'illegal [%s] %s: %s' %
                    ('miscellaneous','subsverbatim',d['subsverbatim']))

    def validate(self):
        """Check the configuration for internal consistancy. Called after all
        configuration files have been loaded."""
        # Heuristic validate that at least one configuration file was loaded.
        if not self.specialchars or not self.tags or not lists:
            raise EAsciiDoc,'incomplete configuration files'
        # Check special characters are only one character long.
        for k in self.specialchars.keys():
            if len(k) != 1:
                raise EAsciiDoc,'[specialcharacters] ' \
                                'must be a single character: %s' % k
        # Check all special words have a corresponding inline macro body.
        for macro in self.specialwords.values():
            if not is_name(macro):
                raise EAsciiDoc,'illegal special word name: %s' % macro
            if not self.sections.has_key(macro):
                warning('missing special word macro: [%s]' % macro)
        # Check all text quotes have a corresponding tag.
        for q in self.quotes.keys():
            tag = self.quotes[q]
            if not tag:
                del self.quotes[q]  # Undefine quote.
            else:
                if tag[0] == '#':
                    tag = tag[1:]
                if not self.tags.has_key(tag):
                    warning('[quotes] %s missing tag definition: %s' % (q,tag))
        # Check all specialsections section names exist.
        for k,v in self.specialsections.items():
            if not self.sections.has_key(v):
                warning('[%s] missing specialsections section' % v)
        paragraphs.validate()
        lists.validate()
        blocks.validate()
        tables.validate()
        macros.validate()

    def is_special_section(self,section_name):
        for name in self.SPECIAL_SECTIONS:
            if re.match(name,section_name):
                return True
        return False

    def dump(self):
        """Dump configuration to stdout."""
        # Header.
        hdr = ''
        hdr = hdr + '#' + writer.newline
        hdr = hdr + '# Generated by AsciiDoc %s for %s %s.%s' % \
            (VERSION,document.backend,document.doctype,writer.newline)
        t = time.asctime(time.localtime(time.time()))
        hdr = hdr + '# %s%s' % (t,writer.newline)
        hdr = hdr + '#' + writer.newline
        sys.stdout.write(hdr)
        # Dump special sections.
        # Dump only the configuration file and command-line attributes.
        # [miscellanous] entries are dumped as part of the [attributes].
        d = {}
        d.update(self.conf_attrs)
        d.update(self.cmd_attrs)
        dump_section('attributes',d)
        Title.dump()
        dump_section('quotes',self.quotes)
        dump_section('specialcharacters',self.specialchars)
        d = {}
        for k,v in self.specialwords.items():
            if d.has_key(v):
                d[v] = '%s "%s"' % (d[v],k)   # Append word list.
            else:
                d[v] = '"%s"' % k
        dump_section('specialwords',d)
        dump_section('replacements',self.replacements)
        dump_section('replacements2',self.replacements2)
        dump_section('specialsections',self.specialsections)
        d = {}
        for k,v in self.tags.items():
            d[k] = '%s|%s' % v
        dump_section('tags',d)
        paragraphs.dump()
        lists.dump()
        blocks.dump()
        tables.dump()
        macros.dump()
        # Dump remaining sections.
        for k in self.sections.keys():
            if not self.is_special_section(k):
                sys.stdout.write('[%s]%s' % (k,writer.newline))
                for line in self.sections[k]:
                    sys.stdout.write('%s%s' % (line,writer.newline))
                sys.stdout.write(writer.newline)

    def subs_section(self,section,d):
        """Section attribute substitution using attributes from
        document.attributes and 'd'.  Lines containing undefinded
        attributes are deleted."""
        if self.sections.has_key(section):
            return subs_attrs(self.sections[section],d)
        else:
            warning('missing [%s] section' % section)
            return ()

    def parse_tags(self):
        """Parse [tags] section entries into self.tags dictionary."""
        d = {}
        parse_entries(self.sections.get('tags',()),d)
        for k,v in d.items():
            if v is None:
                if self.tags.has_key(k):
                    del self.tags[k]
            elif v == 'none':
                self.tags[k] = (None,None)
            else:
                mo = re.match(r'(?P<stag>.*)\|(?P<etag>.*)',v)
                if mo:
                    self.tags[k] = (mo.group('stag'), mo.group('etag'))
                else:
                    raise EAsciiDoc,'[tag] %s value malformed' % k

    def tag(self, name, d=None):
        """Returns (starttag,endtag) tuple named name from configuration file
        [tags] section. Raise error if not found. If a dictionary 'd' is
        passed then merge with document attributes and perform attribute
        substitution on tags."""

        # TODO: Tags should be stored a single string, not split into start
        # and end tags since most are going to be substituted anyway (see
        # subs_tag() for how we should process them. parse_tags() (above)
        # should only validate i.e. parse_check(). This routine should be renamed
        # split_tag() and would call subs_tag(). self.tags dictionary values
        # would be strings not tuples.

        if not self.tags.has_key(name):
            raise EAsciiDoc, 'missing tag: %s' % name
        stag,etag = self.tags[name]
        if d is not None:
            # TODO: Should we warn if substitution drops a tag?
            if stag:
                stag = subs_attrs(stag,d)
            if etag:
                etag = subs_attrs(etag,d)
        if stag is None: stag = ''
        if etag is None: etag = ''
        return (stag,etag)

    def parse_specialsections(self):
        """Parse specialsections section to self.specialsections dictionary."""
        # TODO: This is virtually the same as parse_replacements() and should
        # be factored to single routine.
        d = {}
        parse_entries(self.sections.get('specialsections',()),d,unquote=True)
        for pat,sectname in d.items():
            pat = strip_quotes(pat)
            if not is_regexp(pat):
                raise EAsciiDoc,'[specialsections] entry ' \
                                'is not a valid regular expression: %s' % pat
            if sectname is None:
                if self.specialsections.has_key(pat):
                    del self.specialsections[pat]
            else:
                self.specialsections[pat] = sectname

    def parse_replacements(self,sect='replacements'):
        """Parse replacements section into self.replacements dictionary."""
        replacements = getattr(self,sect)
        d = OrderedDict()
        parse_entries(self.sections.get(sect,()), d, unquote=True)
        for pat,rep in d.items():
            pat = strip_quotes(pat)
            if not is_regexp(pat):
                raise EAsciiDoc,'[%s] entry in %s is not a valid' \
                    ' regular expression: %s' % (sect,self.fname,pat)
            if rep is None:
                if replacements.has_key(pat):
                    del replacements[pat]
            else:
                replacements[pat] = strip_quotes(rep)

    def subs_replacements(self,s,sect='replacements'):
        """Substitute patterns from self.replacements in 's'."""
        result = s
        for pat,rep in getattr(self,sect).items():
            result = re.sub(pat, rep, result)
        return result

    def parse_specialwords(self):
        """Parse special words section into self.specialwords dictionary."""
        reo = re.compile(r'(?:\s|^)(".+?"|[^"\s]+)(?=\s|$)')
        for line in self.sections.get('specialwords',()):
            e = parse_entry(line)
            if not e:
                raise EAsciiDoc,'[specialwords] entry in %s is malformed: %s' \
                    % (self.fname,line)
            name,wordlist = e
            if not is_name(name):
                raise EAsciiDoc,'[specialwords] name in %s is illegal: %s' \
                    % (self.fname,name)
            if wordlist is None:
                # Undefine all words associated with 'name'.
                for k,v in self.specialwords.items():
                    if v == name:
                        del self.specialwords[k]
            else:
                words = reo.findall(wordlist)
                for word in words:
                    word = strip_quotes(word)
                    if not is_regexp(word):
                        raise EAsciiDoc,'[specialwords] entry in %s ' \
                            'is not a valid regular expression: %s' \
                            % (self.fname,word)
                    self.specialwords[word] = name

    def subs_specialchars(self,s):
        """Perform special character substitution on string 's'."""
        """It may seem like a good idea to escape special characters with a '\'
        character, the reason we don't is because the escape character itself
        then has to be escaped and this makes including code listings
        problematic. Use the predefined {amp},{lt},{gt} attributes instead."""
        result = ''
        for ch in s:
            result = result + self.specialchars.get(ch,ch)
        return result

    def subs_specialchars_reverse(self,s):
        """Perform reverse special character substitution on string 's'."""
        result = s
        for k,v in self.specialchars.items():
            result = result.replace(v, k)
        return result

    def subs_specialwords(self,s):
        """Search for word patterns from self.specialwords in 's' and
        substitute using corresponding macro."""
        result = s
        for word in self.specialwords.keys():
            result = re.sub(word, _subs_specialwords, result)
        return result

    def expand_templates(self,section):
        result = []
        for line in self.sections[section]:
            mo = macros.match('+',r'template',line)
            if mo:
                s = mo.group('attrlist')
                if self.sections.has_key(s):
                    result += self.sections[s]
                else:
                    warning('missing [%s] section' % s)
            else:
                result.append(line)
        return result

    def expand_all_templates(self):
        for k in self.sections.keys():
            self.sections[k] = self.expand_templates(k)

    def section2tags(self, section, d={}):
        """Perform attribute substitution on 'section' using document
        attributes plus 'd' attributes. Return tuple (stag,etag) containing
        pre and post | placeholder tags."""
        assert section is not None
        if self.sections.has_key(section):
            body = self.sections[section]
        else:
            warning('missing [%s] section' % section)
            body = ()
        # Split macro body into start and end tag lists.
        stag = []
        etag = []
        in_stag = True
        for s in body:
            if in_stag:
                mo = re.match(r'(?P<stag>.*)\|(?P<etag>.*)',s)
                if mo:
                    if mo.group('stag'):
                        stag.append(mo.group('stag'))
                    if mo.group('etag'):
                        etag.append(mo.group('etag'))
                    in_stag = False
                else:
                    stag.append(s)
            else:
                etag.append(s)
        # Do attribute substitution last so {brkbar} can be used to escape |.
        # But don't do attribute substitution on title -- we've already done it.
        title = d.get('title')
        if title:
            d['title'] = chr(0)  # Replace with unused character.
        stag = subs_attrs(stag, d)
        etag = subs_attrs(etag, d)
        # Put the {title} back.
        if title:
            stag = map(lambda x: x.replace(chr(0), title), stag)
            etag = map(lambda x: x.replace(chr(0), title), etag)
            d['title'] = title
        return (stag,etag)


#---------------------------------------------------------------------------
# Application code.
#---------------------------------------------------------------------------
# Constants
# ---------
APP_DIR = None              # This file's directory.
USER_DIR = None             # ~/.asciidoc
CONF_DIR = '/etc/asciidoc'  # Global configuration files directory.
HELP_FILE = 'help.conf'     # Default (English) help file.

# Globals
# -------
document = Document()       # The document being processed.
config = Config()           # Configuration file reader.
reader = Reader()           # Input stream line reader.
writer = Writer()           # Output stream line writer.
paragraphs = Paragraphs()   # Paragraph definitions.
lists = Lists()             # List definitions.
blocks = DelimitedBlocks()  # DelimitedBlock definitions.
tables = Tables()           # Table definitions.
macros = Macros()           # Macro definitions.
calloutmap = CalloutMap()   # Coordinates callouts and callout list.

def asciidoc(backend, doctype, confiles, infile, outfile, options):
    """Convert AsciiDoc document to DocBook document of type doctype
    The AsciiDoc document is read from file object src the translated
    DocBook file written to file object dst."""
    try:
        if doctype not in ('article','manpage','book'):
            raise EAsciiDoc,'illegal document type'
        if backend == 'linuxdoc' and doctype != 'article':
            raise EAsciiDoc,'%s %s documents are not supported' \
                            % (backend,doctype)
        document.backend = backend
        if not os.path.exists(os.path.join(APP_DIR, backend+'.conf')) and not \
               os.path.exists(os.path.join(CONF_DIR, backend+'.conf')):
            warning('non-standard %s backend' % backend, linenos=False)
        document.doctype = doctype
        document.infile = infile
        document.init_attrs()
        # Set processing options.
        for o in options:
            if o == '-c': config.dumping = True
            if o == '-s': config.header_footer = False
            if o == '-v': config.verbose = True
        # Check the infile exists.
        if infile != '<stdin>' and not os.path.isfile(infile):
            raise EAsciiDoc,'input file %s missing' % infile
        if '-e' not in options:
            # Load global configuration from system configuration directory.
            config.load_all(CONF_DIR)
            # Load global configuration files from asciidoc directory.
            config.load_all(APP_DIR)
            # Load configuration files from ~/.asciidoc if it exists.
            if USER_DIR is not None:
                config.load_all(USER_DIR)
            # Load configuration files from document directory.
            if infile != '<stdin>':
                config.load_all(os.path.dirname(infile))
        if infile != '<stdin>':
            # Load implicit document specific configuration files if they exist.
            config.load(os.path.splitext(infile)[0] + '.conf')
            config.load(os.path.splitext(infile)[0] + '-' + backend + '.conf')
        # If user specified configuration file(s) overlay the defaults.
        if confiles:
            for conf in confiles:
                if os.path.isfile(conf):
                    config.load(conf)
                else:
                    raise EAsciiDoc,'configuration file %s missing' % conf
        document.init_attrs()   # Add conf files.
        # Check configuration for consistency.
        config.validate()
        # Build outfile name now all conf files have been read.
        if outfile is None:
            outfile = os.path.splitext(infile)[0] + '.' + backend
            if config.outfilesuffix:
                # Change file extension.
                outfile = os.path.splitext(outfile)[0] + config.outfilesuffix
        document.outfile = outfile
        if config.dumping:
            config.dump()
        else:
            reader.tabsize = config.tabsize
            reader.open(infile)
            try:
                writer.newline = config.newline
                writer.open(outfile)
                try:
                    document.init_attrs()   # Add file name related entries.
                    document.translate()
                finally:
                    writer.close()
            finally:
                reader.closefile()  # Keep reader state for postmortem.
    except (KeyboardInterrupt, SystemExit):
        print
    except Exception,e:
        # Cleanup.
        if outfile and outfile != '<stdout>' and os.path.isfile(outfile):
            os.unlink(outfile)
        # Build and print error description.
        msg = 'FAILED: '
        if reader.cursor:
            msg = msg + '%s: line %d: ' % (reader.cursor[0],reader.cursor[1])
        if isinstance(e,EAsciiDoc):
            print_stderr(msg+str(e))
        else:
            print_stderr(msg+'unexpected error:')
            print_stderr('-'*60)
            traceback.print_exc(file=sys.stderr)
            print_stderr('-'*60)
        sys.exit(1)

def usage(msg=''):
    if msg:
        print_stderr(msg)
    show_help('default', sys.stderr)

def show_help(topic, stream=sys.stdout):
    """Print help topic to stdout."""
    # Select help file.
    lang = config.cmd_attrs.get('lang')
    if lang and lang != 'en':
        help_file = 'help-' + lang + '.conf'
    else:
        help_file = HELP_FILE
    # Print [topic] section from help file.
    topics = OrderedDict()
    load_sections(topics, help_file, CONF_DIR)
    load_sections(topics, help_file, APP_DIR)
    if USER_DIR is not None:
        load_sections(topics, help_file, USER_DIR)
    if len(topics) == 0:
        # Default to English if specified language help files not found.
        help_file = HELP_FILE
        load_sections(topics, help_file, CONF_DIR)
        load_sections(topics, help_file, APP_DIR)
    if len(topics) == 0:
        print_stderr('no help topics found')
        sys.exit(1)
    n = 0
    for k in topics.keys():
        if re.match(re.escape(topic), k):
            n += 1
            lines = topics[k]
    if n == 0:
        print_stderr('help topic not found: [%s] in %s' % (topic, help_file))
        print_stderr('available help topics: %s' % ', '.join(topics.keys()))
        sys.exit(1)
    elif n > 1:
        print_stderr('ambiguous help topic: %s' % topic)
    else:
        for line in lines:
            print >>stream, line

def main():
    if float(sys.version[:3]) < 2.3:
        print_stderr('FAILED: Python 2.3 or better required.')
        sys.exit(1)
    # Locate the executable and configuration files directory.
    global APP_DIR,USER_DIR
    APP_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
    USER_DIR = os.environ.get('HOME')
    if USER_DIR is not None:
        USER_DIR = os.path.join(USER_DIR,'.asciidoc')
        if not os.path.isdir(USER_DIR):
            USER_DIR = None
    # Process command line options.
    import getopt
    try:
        #DEPRECATED: --safe option.
        opts,args = getopt.getopt(sys.argv[1:],
            'a:b:cd:ef:hno:svw:',
            ['attribute=','backend=','conf-file=','doctype=','dump-conf',
            'help','no-conf','no-header-footer','out-file=','profile',
            'section-numbers','verbose','version','safe','unsafe'])
    except getopt.GetoptError:
        usage()
        sys.exit(1)
    if len(args) > 1:
        usage()
        sys.exit(1)
    backend = DEFAULT_BACKEND
    doctype = DEFAULT_DOCTYPE
    confiles = []
    outfile = None
    options = []
    prof = False
    help_option = False
    for o,v in opts:
        if o in ('--help','-h'):
            help_option = True
        if o == '--profile':
            prof = True
        if o == '--unsafe':
            document.safe = False
        if o == '--version':
            print('asciidoc %s' % VERSION)
            sys.exit(0)
        if o in ('-b','--backend'):
            backend = v
        if o in ('-c','--dump-conf'):
            options.append('-c')
        if o in ('-d','--doctype'):
            doctype = v
        if o in ('-e','--no-conf'):
            options.append('-e')
        if o in ('-f','--conf-file'):
            confiles.append(v)
        if o in ('-n','--section-numbers'):
            o = '-a'
            v = 'numbered'
        if o in ('-a','--attribute'):
            e = parse_entry(v, allow_name_only=True)
            if not e:
                usage('Illegal -a option: %s' % v)
                sys.exit(1)
            k,v = e
            # A @ suffix denotes don't override existing document attributes.
            if v and v[-1] == '@':
                document.attributes[k] = v[:-1]
            else:
                config.cmd_attrs[k] = v
        if o in ('-o','--out-file'):
            if v == '-':
                outfile = '<stdout>'
            else:
                outfile = v
        if o in ('-s','--no-header-footer'):
            options.append('-s')
        if o in ('-v','--verbose'):
            options.append('-v')
    if help_option:
        if len(args) == 0:
            show_help('default')
        else:
            show_help(args[-1])
        sys.exit(0)
    if len(args) == 0 and len(opts) == 0:
        usage()
        sys.exit(1)
    if len(args) == 0:
        usage('No source file specified')
        sys.exit(1)
    if not backend:
        usage('No --backend option specified')
        sys.exit(1)
    if args[0] == '-':
        infile = '<stdin>'
    else:
        infile = args[0]
    if infile == '<stdin>' and not outfile:
        outfile = '<stdout>'
    # Convert in and out files to absolute paths.
    if infile != '<stdin>':
        infile = os.path.abspath(infile)
    if outfile and outfile != '<stdout>':
        outfile = os.path.abspath(outfile)
    # Do the work.
    if prof:
        import profile
        profile.run("asciidoc('%s','%s',(),'%s',None,())"
            % (backend,doctype,infile))
    else:
        asciidoc(backend, doctype, confiles, infile, outfile, options)
    if document.has_errors:
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except SystemExit:
        raise
    except:
        print_stderr('%s: unexpected error: %s' %
                (os.path.basename(sys.argv[0]), sys.exc_info()[1]))
        print_stderr('-'*60)
        traceback.print_exc(file=sys.stderr)
        print_stderr('-'*60)
        sys.exit(1)
