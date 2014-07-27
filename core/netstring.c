
/* Use this file as a template to start implementing a module that
   also declares object types. All occurrences of 'Xxo' should be changed
   to something reasonable for your objects. After that, all other
   occurrences of 'xx' should be changed to something reasonable for your
   module. If your module is named decode your sourcefile should be named
   foomodule.c.

   You will probably want to delete all references to 'x_attr' and add
   your own types of attributes instead.  Maybe you want to name your
   local variables other than 'self'.  If your object type is needed in
   other files, you'll have to create a file "foobarobject.h"; see
   floatobject.h for an example. */


#include <stddef.h>
#include <sys/socket.h>

#include "Python.h"


PyDoc_STRVAR(netstring_encode_doc,
"encode(b)\n\
\n\
Return a bytes that encodeds the given byte string.");

static PyObject *
netstring_encode(PyObject *self, PyObject *args)
{
    PyObject *src = NULL;
    char *srcbuf;
    Py_ssize_t srclen;
    PyObject *dst = NULL;
    char *dstbuf;
    int o;

    if (PyArg_UnpackTuple(args, "src", 1, 1, &src)) {
        if (PyBytes_Check(src)) {
            srclen = PyBytes_GET_SIZE(src);
            srcbuf = PyBytes_AS_STRING(src);
            dst = PyBytes_FromStringAndSize(NULL, srclen+23);
            if (!dst)
                return NULL;
            dstbuf = PyBytes_AS_STRING(dst);
            o = sprintf(dstbuf, "%lu:", (unsigned long) srclen);
            memcpy((void *) dstbuf + o, (void *) srcbuf, (size_t) srclen);
            o += srclen;
            dstbuf[o++] = ',';
            if (o != srclen+23 && _PyBytes_Resize(&dst, o) < 0) {
                Py_XDECREF(dst);
                return NULL;
            }
        } else {
            PyErr_SetString(PyExc_TypeError, "netstring.encode needs a bytes object.");
            return NULL;
        }
    }
    return dst;
}


PyDoc_STRVAR(netstring_decode_doc,
"decode(b)\n\
\n\
Decode a netstring (as bytes) return byte string.");

static PyObject *
netstring_decode(PyObject *self, PyObject *args)
{
    PyObject *src = NULL;
    char *srcbuf;
    Py_ssize_t srclen;
    PyObject *dst = NULL;
    char *dstbuf;
    unsigned long slen;
    int o;

    if (PyArg_UnpackTuple(args, "src", 1, 1, &src)) {
        if (PyBytes_Check(src)) {
            srcbuf = PyBytes_AS_STRING(src);
            srclen = PyBytes_GET_SIZE(src);
            o = sscanf(srcbuf, "%21lu:",&slen);
            if (o == EOF) {
                return PyErr_SetFromErrno(PyExc_OSError);
            }
            if (o < 1) {
                PyErr_SetString(PyExc_ValueError, "netstring.decode malformed length.");
                return NULL;
            }
            srcbuf = strchr(srcbuf, ':');
            if (srcbuf == NULL) {
                PyErr_SetString(PyExc_ValueError, "netstring.decode malformed prefix.");
                return NULL;
            }
            if (slen > srclen) {
                PyErr_SetString(PyExc_OverflowError, "source string is too large");
                return NULL;
            }
            if (srcbuf[slen+1] != ',') {
                PyErr_SetString(PyExc_ValueError, "netstring.decode malformed end.");
                return NULL;
            }
            dst = PyBytes_FromStringAndSize(NULL, slen);
            if (!dst)
                return NULL;
            dstbuf = PyBytes_AS_STRING(dst);
            memcpy((void *) dstbuf, (void *) ++srcbuf, (size_t) slen);
            return dst;
        } else {
            PyErr_SetString(PyExc_TypeError, "netstring.decode needs a bytes object.");
            return NULL;
        }
    }
    return NULL;
}

PyDoc_STRVAR(netstring_decode_stream_doc,
"decode_stream(socket)\n\
\n\
Decode a netstring read from a socket, return decoded bytes,");

static PyObject *
netstring_decode_stream(PyObject *self, PyObject *args)
{
    PyObject *stream = NULL;
    PyObject *dst = NULL;
    int sockfd = -1;
    char buf[22];
    char *bp;
    ssize_t rcvlen;
    unsigned long slen;
    int o;

    if (PyArg_UnpackTuple(args, "stream", 1, 1, &stream)) {
        if ((sockfd = PyObject_AsFileDescriptor(stream)) < 0) {
            return NULL;
        }
        Py_BEGIN_ALLOW_THREADS
        rcvlen = recv(sockfd, (void *) buf, 22, MSG_PEEK);
        Py_END_ALLOW_THREADS
        if (rcvlen < 0) {
            return PyErr_SetFromErrno(PyExc_IOError);
        }
        o = sscanf(buf, "%21lu:",&slen);
        if (o == EOF) {
            return PyErr_SetFromErrno(PyExc_OSError);
        }
        if (o < 1) {
            PyErr_SetString(PyExc_ValueError, "netstring.decode_stream malformed length.");
            return NULL;
        }
        bp = strchr(buf, ':');
        if (bp == NULL) {
            PyErr_SetString(PyExc_ValueError, "netstring.decode_stream malformed prefix.");
            return NULL;
        }
        bp++;
        // discard length header
        Py_BEGIN_ALLOW_THREADS
        recv(sockfd, (void *) buf, bp-buf, 0);
        Py_END_ALLOW_THREADS
        // Read string into new bytes object.
        dst = PyBytes_FromStringAndSize(NULL, slen);
        if (!dst)
            return NULL;
        bp = PyBytes_AS_STRING(dst);
        Py_BEGIN_ALLOW_THREADS
        rcvlen = recv(sockfd, (void *) bp, slen, 0);
        Py_END_ALLOW_THREADS
        if (rcvlen < 0) {
            return PyErr_SetFromErrno(PyExc_IOError);
        }
        recv(sockfd, (void *) buf, 1, 0);
        if (buf[0] != ',') {
                PyErr_SetString(PyExc_ValueError, "netstring.decode malformed end.");
                return NULL;
        }
        return dst;
    } else {
        return NULL;
    }
    return NULL;
}



/* List of functions defined in the module */

static PyMethodDef netstring_methods[] = {
    {"encode",             netstring_encode, METH_VARARGS, netstring_encode_doc},
    {"decode",             netstring_decode, METH_VARARGS, netstring_decode_doc},
    {"decode_stream",      netstring_decode_stream, METH_VARARGS, netstring_decode_stream_doc},
    {NULL, NULL, 0, NULL}           /* sentinel */
};

PyDoc_STRVAR(module_doc,
"Implements a netstring object, as described in:\n\n"
"http://cr.yp.to/proto/netstrings.txt\n");


static struct PyModuleDef netstringmodule = {
    PyModuleDef_HEAD_INIT,
    "netstring",
    module_doc,
    -1,
    netstring_methods,
    NULL,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC
PyInit_netstring(void)
{
    PyObject *m = NULL;

    m = PyModule_Create(&netstringmodule);
    if (m == NULL)
        goto fail;
    return m;
 fail:
    Py_XDECREF(m);
    return NULL;
}
