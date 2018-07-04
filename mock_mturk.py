#!/usr/bin/env python
import glob
import os
import csv
import urlparse
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer


def sane_path(path):
    frags = path.split('/')
    newFrags = []
    for token in frags:
        if token == '.':
            continue
        if token == '..':
            if len(newFrags) > 0:
                newFrags.pop()
                continue
            else:
                raise Exception('Path cannot be resolved outside root dir')
        newFrags.append(token)
    return '/'.join(newFrags)
            

def TurkHandlerFactory(datafile):
    RECORDS = []
    with open(datafile, 'r') as f:
        headers = None
        reader = csv.reader(f, delimiter=',', quotechar='"')
        for record in reader:
            if headers is None:
                headers = record
                continue
            recordObj = {}
            for i, header in enumerate(headers):
                recordObj[header] = record[i] if i < len(record) else None
            RECORDS.append(recordObj)

    class TurkLikeHandler(BaseHTTPRequestHandler):
        records = RECORDS

        def _list_directory(self):
            self.wfile.write('<html><head><title>Listing</title></head><body>')
            self.wfile.write('<h2>Available Pages</h2>')
            self.wfile.write('<ul>')
            for f in glob.glob('*.html') + glob.glob('*.htm'):
                filename = os.path.basename(f)
                self.wfile.write('<li><a href="/0/{}">{}</a></li>'.format(filename, filename))
            self.wfile.write('</ul>')
            self.wfile.write('</body></html>')

        def _replace_data(self, record_id, string):
            record = self.records[record_id]
            for v in record:
                if record[v] is None:
                    continue
                string = string.replace('${' + str(v) + '}', record[v])
            return string

        def _render_page(self, record_id, path):
            if record_id < 0 or record_id >= len(self.records):
                self.send_response(404)
                self.send_header('Content-type','text/html')
                self.end_headers()
                self.wfile.write('Input record does not exist')
                return
            if os.path.splitext(path)[1] == '.js':
                self.send_response(200)
                self.send_header('Content-type','application/javascript')
                self.end_headers()
                with open(path, 'r') as f:
                    self.wfile.write(f.read())
                return
            if os.path.splitext(path)[1] == '.css':
                self.send_response(200)
                self.send_header('Content-type','text/css')
                self.end_headers()
                with open(path, 'r') as f:
                    self.wfile.write(read.f())
                return
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write('<html><head><title>HIT Demo Page</title></head><body>')
            self.wfile.write('<div class="clearfix" style="padding: 20px; text-align: center; background: #ff0;">' + 
                '<a class="btn btn-primary float-left" href="/{}/{}">&larr;</a>'.format(max(record_id - 1, 0), path) + 
                '<a class="btn btn-primary float-right" href="/{}/{}">&rarr;</a>'.format(
                    min(record_id + 1, len(self.records) - 1), path) + 
                '<h3>Use buttons to toggle page. Click <a href="/">here</a> to return.</h3></div>')
            self.wfile.write('<form method="post" action="/post-receive-hook">')
            with open(path, 'r') as f:
                for line in f:
                    self.wfile.write(self._replace_data(record_id, line))
            self.wfile.write('<div style="text-align: center">' + 
                '<input type="submit" value="Submit"  class="btn btn-primary"/></div>')
            self.wfile.write('</form>')
            self.wfile.write('</body></html>');

        def do_POST(self):
            if self.path == '/post-receive-hook':
                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()
                length = int(self.headers['Content-Length'])
                post_data = urlparse.parse_qs(self.rfile.read(length).decode('utf-8'))
                self.wfile.write('<html><head><title>Got Data</title></head><body>');
                self.wfile.write('<h2>POST Response Details</h2><table><tr><td>Key</td><td>Value</td></tr>');
                for key, value in post_data.iteritems():
                    self.wfile.write("<tr><td>{}</td><td>{}</td></tr>".format(key, value))
                self.wfile.write('</table></body></html>');
            else:
                self.do_GET()

        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()
                self._list_directory()
                return
            else:
                try:
                    template = sane_path("/".join(self.path.split('/')[2:]))
                except Exception:
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write('Bad Request')
                    return
                data_record_id = int(self.path.split('/')[1])
                if os.path.isfile(template):
                    self._render_page(data_record_id, template)
                else:
                    self.send_response(404)
                    self.send_header('Content-type','text/html')
                    self.end_headers()
                    self.wfile.write('File not found.')
                return
    return TurkLikeHandler

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print '{} - [data file] ([port] = 8080)'.format(sys.argv[1])
        print '    [data file] : csv file containing data to use'
        exit(1)
    dfile = sys.argv[1]
    port = sys.argv[2] if len(sys.argv) > 2 else 8080
    if not os.path.isfile(dfile):
        raise Exception('Data file specified does not exist')

    try:
        server = HTTPServer(('127.0.0.1', port), TurkHandlerFactory(dfile))
        print 'Starting local debug server on {} w/ file {}'.format(port, dfile)
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down the web server'
        server.socket.close()
