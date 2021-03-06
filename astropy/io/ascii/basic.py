# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""An extensible ASCII table reader and writer.

basic.py:
  Basic table read / write functionality for simple character
  delimited files with various options for column header definition.

:Copyright: Smithsonian Astrophysical Observatory (2011)
:Author: Tom Aldcroft (aldcroft@head.cfa.harvard.edu)
"""

from __future__ import absolute_import, division, print_function

import re

import numpy as np

from . import core


class Basic(core.BaseReader):
    """Read a character-delimited table with a single header line at the top
    followed by data lines to the end of the table.  Lines beginning with # as
    the first non-whitespace character are comments.  This reader is highly
    configurable.
    ::

        rdr = ascii.get_reader(Reader=ascii.Basic)
        rdr.header.splitter.delimiter = ' '
        rdr.data.splitter.delimiter = ' '
        rdr.header.start_line = 0
        rdr.data.start_line = 1
        rdr.data.end_line = None
        rdr.header.comment = r'\s*#'
        rdr.data.comment = r'\s*#'

    Example table::

      # Column definition is the first uncommented line
      # Default delimiter is the space character.
      apples oranges pears

      # Data starts after the header column definition, blank lines ignored
      1 2 3
      4 5 6
    """
    _format_name = 'basic'
    _description = 'Basic table with custom delimiters'

    def __init__(self):
        core.BaseReader.__init__(self)
        self.header.splitter.delimiter = ' '
        self.data.splitter.delimiter = ' '
        self.header.start_line = 0
        self.data.start_line = 1
        self.header.comment = r'\s*#'
        self.header.write_comment = '# '
        self.data.comment = r'\s*#'
        self.data.write_comment = '# '


class NoHeader(Basic):
    """Read a table with no header line.  Columns are autonamed using
    header.auto_format which defaults to "col%d".  Otherwise this reader
    the same as the :class:`Basic` class from which it is derived.  Example::

      # Table data
      1 2 "hello there"
      3 4 world
    """
    _format_name = 'no_header'
    _description = 'Basic table with no headers'

    def __init__(self):
        Basic.__init__(self)
        self.header.start_line = None
        self.data.start_line = 0


class CommentedHeaderHeader(core.BaseHeader):
    """Header class for which the column definition line starts with the
    comment character.  See the :class:`CommentedHeader` class  for an example.
    """
    def process_lines(self, lines):
        """Return only lines that start with the comment regexp.  For these
        lines strip out the matching characters."""
        re_comment = re.compile(self.comment)
        for line in lines:
            match = re_comment.match(line)
            if match:
                yield line[match.end():]

    def write(self, lines):
        lines.append(self.write_comment + self.splitter.join(self.colnames))


class CommentedHeader(core.BaseReader):
    """Read a file where the column names are given in a line that begins with
    the header comment character. `header_start` can be used to specify the
    line index of column names, and it can be a negative index (for example -1
    for the last commented line).  The default delimiter is the <space>
    character.::

      # col1 col2 col3
      # Comment line
      1 2 3
      4 5 6
    """
    _format_name = 'commented_header'
    _description = 'Column names in a commented line'

    def __init__(self):
        core.BaseReader.__init__(self)
        self.header = CommentedHeaderHeader()
        self.header.data = self.data
        self.data.header = self.header
        self.header.splitter.delimiter = ' '
        self.data.splitter.delimiter = ' '
        self.header.start_line = 0
        self.data.start_line = 0
        self.header.comment = r'\s*#'
        self.header.write_comment = '# '
        self.data.comment = r'\s*#'
        self.data.write_comment = '# '


class Tab(Basic):
    """Read a tab-separated file.  Unlike the :class:`Basic` reader, whitespace is
    not stripped from the beginning and end of lines.  By default whitespace is
    still stripped from the beginning and end of individual column values.

    Example::

      col1 <tab> col2 <tab> col3
      # Comment line
      1 <tab> 2 <tab> 5
    """
    _format_name = 'tab'
    _description = 'Basic table with tab-separated values'

    def __init__(self):
        Basic.__init__(self)
        self.header.splitter.delimiter = '\t'
        self.data.splitter.delimiter = '\t'
        # Don't strip line whitespace since that includes tabs
        self.header.splitter.process_line = None
        self.data.splitter.process_line = None
        # Don't strip data value whitespace since that is significant in TSV tables
        self.data.splitter.process_val = None
        self.data.splitter.skipinitialspace = False


class Csv(Basic):
    """Read a CSV (comma-separated-values) file.

    Example::

      num,ra,dec,radius,mag
      1,32.23222,10.1211,0.8,18.1
      2,38.12321,-88.1321,2.2,17.0

    Plain csv (comma separated value) files typically contain as many entries
    as there are columns on each line. In contrast, common spreadsheed editors
    stop writing if all remaining cells on a line are empty, which can lead to
    lines where the rightmost entries are missing. This Reader can deal with
    such files.
    Masked values (indicated by an empty '' field value when reading) are
    written out in the same way with an empty ('') field.  This is different
    from the typical default for `io.ascii` in which missing values are
    indicated by ``--``.

    Example::

      num,ra,dec,radius,mag
      1,32.23222,10.1211
      2,38.12321,-88.1321,2.2,17.0
    """
    _format_name = 'csv'
    _io_registry_suffix = '.csv'
    _io_registry_can_write = True
    _description = 'Comma-separated-values'

    def __init__(self):
        core.BaseReader.__init__(self)
        self.data.splitter.delimiter = ','
        self.header.splitter.delimiter = ','
        self.header.start_line = 0
        self.data.start_line = 1
        self.data.fill_values = [(core.masked, '')]

    def inconsistent_handler(self, str_vals, ncols):
        '''Adjust row if it is too short.

        If a data row is shorter than the header, add empty values to make it the
        right length.
        Note that this will *not* be called if the row already matches the header.

        :param str_vals: A list of value strings from the current row of the table.
        :param ncols: The expected number of entries from the table header.
        :returns:
            list of strings to be parsed into data entries in the output table.
        '''
        if len(str_vals) < ncols:
            str_vals.extend((ncols - len(str_vals)) * [''])

        return str_vals


class Rdb(Tab):
    """Read a tab-separated file with an extra line after the column definition
    line.  The RDB format meets this definition.  Example::

      col1 <tab> col2 <tab> col3
      N <tab> S <tab> N
      1 <tab> 2 <tab> 5

    In this reader the second line is just ignored.
    """
    _format_name = 'rdb'
    _io_registry_format_aliases = ['rdb']
    _io_registry_suffix = '.rdb'
    _description = 'Tab-separated with a type definition header line'

    def __init__(self):
        Tab.__init__(self)
        self.header = RdbHeader()
        self.header.start_line = 0
        self.header.comment = r'\s*#'
        self.header.write_comment = '# '
        self.header.splitter.delimiter = '\t'
        self.header.splitter.process_line = None
        self.header.data = self.data
        self.data.header = self.header
        self.data.start_line = 2


class RdbHeader(core.BaseHeader):
    col_type_map = {'n': core.NumType,
                    's': core.StrType}

    def get_type_map_key(self, col):
        return col.raw_type[-1]

    def get_cols(self, lines):
        """Initialize the header Column objects from the table ``lines``.

        This is a specialized get_cols for the RDB type:
        Line 0: RDB col names
        Line 1: RDB col definitions
        Line 2+: RDB data rows

        :param lines: list of table lines
        :returns: None
        """
        header_lines = self.process_lines(lines)   # this is a generator
        header_vals_list = [hl for _, hl in zip(range(2), self.splitter(header_lines))]
        if len(header_vals_list) != 2:
            raise ValueError('RDB header requires 2 lines')
        self.names, raw_types = header_vals_list

        if len(self.names) != len(raw_types):
            raise ValueError('RDB header mismatch between number of column names and column types')

        if any(not re.match(r'\d*(N|S)$', x, re.IGNORECASE) for x in raw_types):
            raise ValueError('RDB types definitions do not all match [num](N|S): %s' % raw_types)

        self._set_cols_from_names()
        for col, raw_type in zip(self.cols, raw_types):
            col.raw_type = raw_type
            col.type = self.get_col_type(col)

    def write(self, lines):
        lines.append(self.splitter.join(self.colnames))
        rdb_types = []
        for col in self.cols:
            # Check if dtype.kind is string or unicode.  See help(np.core.numerictypes)
            rdb_type = 'S' if col.dtype.kind in ('S', 'U') else 'N'
            rdb_types.append(rdb_type)

        lines.append(self.splitter.join(rdb_types))
