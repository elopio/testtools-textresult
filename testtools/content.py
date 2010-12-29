# Copyright (c) 2009 Jonathan M. Lange. See LICENSE for details.

"""Content - a MIME-like Content object."""

import codecs

from testtools.compat import _b
from testtools.content_type import ContentType, UTF8_TEXT
from testtools.testresult import TestResult


_join_b = _b("").join


DEFAULT_CHUNK_SIZE = 4096


def _iter_chunks(stream, chunk_size):
    """Read 'stream' in chunks of 'chunk_size'.

    :param stream: A file-like object to read from.
    :param chunk_size: The size of each read from 'stream'.
    """
    chunk = stream.read(chunk_size)
    while chunk:
        yield chunk
        chunk = stream.read(chunk_size)


class Content(object):
    """A MIME-like Content object.

    Content objects can be serialised to bytes using the iter_bytes method.
    If the Content-Type is recognised by other code, they are welcome to
    look for richer contents that mere byte serialisation - for example in
    memory object graphs etc. However, such code MUST be prepared to receive
    a generic Content object that has been reconstructed from a byte stream.

    :ivar content_type: The content type of this Content.
    """

    def __init__(self, content_type, get_bytes):
        """Create a ContentType."""
        if None in (content_type, get_bytes):
            raise ValueError("None not permitted in %r, %r" % (
                content_type, get_bytes))
        self.content_type = content_type
        self._get_bytes = get_bytes

    def __eq__(self, other):
        return (self.content_type == other.content_type and
            _join_b(self.iter_bytes()) == _join_b(other.iter_bytes()))

    @classmethod
    def from_file(cls, path, content_type=None, chunk_size=None):
        """Create a `Content` object from a file on disk.

        Note that the file will only be read from when ``iter_bytes`` is
        called.

        :param path: The path to the file to be used as content.
        :param content_type: The type of content.  If not specified, defaults
            to UTF8-encoded text/plain.
        :param chunk_size: The size of chunks to read from the file.
             Defaults to `DEFAULT_CHUNK_SIZE`.
        """
        if content_type is None:
            content_type = UTF8_TEXT
        if chunk_size is None:
            chunk_size = DEFAULT_CHUNK_SIZE
        def read_file():
            stream = open(path, 'rb')
            for chunk in _iter_chunks(stream, chunk_size):
                yield chunk
            stream.close()
        return cls(content_type, read_file)

    @classmethod
    def from_stream(cls, stream, content_type=None, chunk_size=None):
        """Create a `Content` object from a file-like stream.

        Note that the stream will only be read from when ``iter_bytes`` is
        called.

        :param stream: A file-like object to read the content from.
        :param content_type: The type of content. If not specified, defaults
            to UTF8-encoded text/plain.
        :param chunk_size: The size of chunks to read from the file.
             Defaults to `DEFAULT_CHUNK_SIZE`.
        """
        if content_type is None:
            content_type = UTF8_TEXT
        if chunk_size is None:
            chunk_size = DEFAULT_CHUNK_SIZE
        return Content(content_type, lambda: _iter_chunks(stream, chunk_size))

    @classmethod
    def from_text(cls, text):
        """Create a `Content` object from some text.

        This is useful for adding details which are short strings.
        """
        return cls(UTF8_TEXT, lambda: [text.encode('utf8')])

    def iter_bytes(self):
        """Iterate over bytestrings of the serialised content."""
        return self._get_bytes()

    def iter_text(self):
        """Iterate over the text of the serialised content.

        This is only valid for text MIME types, and will use ISO-8859-1 if
        no charset parameter is present in the MIME type. (This is somewhat
        arbitrary, but consistent with RFC2617 3.7.1).

        :raises ValueError: If the content type is not text/\*.
        """
        if self.content_type.type != "text":
            raise ValueError("Not a text type %r" % self.content_type)
        return self._iter_text()

    def _iter_text(self):
        """Worker for iter_text - does the decoding."""
        encoding = self.content_type.parameters.get('charset', 'ISO-8859-1')
        try:
            # 2.5+
            decoder = codecs.getincrementaldecoder(encoding)()
            for bytes in self.iter_bytes():
                yield decoder.decode(bytes)
            final = decoder.decode(_b(''), True)
            if final:
                yield final
        except AttributeError:
            # < 2.5
            bytes = ''.join(self.iter_bytes())
            yield bytes.decode(encoding)

    def __repr__(self):
        return "<Content type=%r, value=%r>" % (
            self.content_type, _join_b(self.iter_bytes()))


class TracebackContent(Content):
    """Content object for tracebacks.

    This adapts an exc_info tuple to the Content interface.
    text/x-traceback;language=python is used for the mime type, in order to
    provide room for other languages to format their tracebacks differently.
    """

    def __init__(self, err, test):
        """Create a TracebackContent for err."""
        if err is None:
            raise ValueError("err may not be None")
        content_type = ContentType('text', 'x-traceback',
            {"language": "python", "charset": "utf8"})
        self._result = TestResult()
        value = self._result._exc_info_to_unicode(err, test)
        super(TracebackContent, self).__init__(
            content_type, lambda: [value.encode("utf8")])


def text_content(text):
    """Create a `Content` object from some text.

    This is useful for adding details which are short strings.
    """
    return Content.from_text(text)
