#coding:utf-8

import os.path
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

class UserHander(tornado.web.RequestHandler):
    def post(self):
        userName = self.get_argument("username")
        userEmail = self.get_argument("email")
        userWebsite = self.get_argument("website")
        userLanguage = self.get_argument("language")
        self.render("user.html", username = userName, email = userEmail, website = userWebsite, language = userLanguage)

handlers = [
    (r"/", IndexHandler),
    (r"/user", UserHander)
]

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", IndexHandler),
            (r"/user", UserHander)
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "template"),
            debug=True
        )
        tornado.web.Application.__init__(self, handlers, **settings)



def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
