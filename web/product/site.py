#coding:utf-8
import os.path   #ioport 导入os模块
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import torndb
import json
import datetime
from tornado.options import define, options
#定义全局变量
define("port", default=9000, help="listen on the given port", type=int)
define("host", default="0.0.0.0", help="listen on the given host")
define("mysql_host", default="dev-zg6wlg88g.quixey.be", help="blog database host")
define("mysql_database", default="report", help="blog database name")
define("mysql_user", default="quixey", help="blog database user")
define("mysql_password", default="Dev@Quixey2016", help="blog database password")

LIMIT_IN_FULL_LIST=1
LIMIT_IN_APP_LIST=5
LIMIT_IN_FUNCTION_LIST=100

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", IndexHandler),
            (r"/envs/([a-z0-9-]*)/pipeline", pipelineHandler),
            (r"/envs/([a-z0-9-]*)/pipeline/([a-zA-Z0-9._-]*)",pipelineHandler),
            (r"/envs/([a-z0-9-]*)/pipeline/([a-zA-Z0-9._-]*)/([a-zA-Z0-9._-]*)", pipelineHandler),


            (r"/envs/([a-z0-9-]*)/cpStatistics",cpStatisticsHandler),
            (r"/envs/([a-z0-9-]*)/cpStatistics/([a-zA-Z0-9._-]*)",cpStatisticsHandler),
            (r"/envs/([a-z0-9-]*)/cpStatistics/([a-zA-Z0-9._-]*)/([a-zA-Z0-9._-]*)", cpStatisticsHandler),

            (r"/envs/([a-z0-9-]*)/chart",chartHandler),
            (r"/envs/([a-z0-9-]*)/chart/([a-zA-Z0-9._-]*)",chartHandler),
            (r"/envs/([a-z0-9-]*)/chart/([a-zA-Z0-9._-]*)/([a-zA-Z0-9._-]*)", chartHandler),

            (r"/envs/([a-z0-9-]*)/jobs/([a-zA-Z0-9-]*)/([\s\S]*)",PipelineJobHandler),

        ]

        settings = dict(
            blog_title=u"Tornado Blog",
            template_path=os.path.join(os.path.dirname(__file__), "template"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            #ui_modules={"Entry": EntryModule},
            xsrf_cookies=True,
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            login_url="/auth/login",
            debug=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        self.db = torndb.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)

class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

class IndexHandler(BaseHandler):
    def get(self,env=None,path=None,app=None,function=None):
        suffix = "/%s/%s/%s/%s" % (env,path,app, function) if app and function else "/%s/%s/%s" % (env,path,app) if app else ""
        print suffix
        self.render("cp_index.html", suffix=suffix)
class cpStatisticsHandler(BaseHandler):
    def get(self,env,app=None,function=None):
        # set limit for full list, app list and app+function list
        limit = LIMIT_IN_FUNCTION_LIST if app and function else LIMIT_IN_APP_LIST if app else LIMIT_IN_FULL_LIST
        suffix = "/%s/%s" % (app, function) if app and function else "/%s" % app if app else ""
        #app="kugou.com"
        #function="showRecording"
        #env="stage03"
        tableName="cpStatistics_report_"+env
        where=""
        if app:
            where = where + " app='%s'" % app
        else:
            where = where +"time in (SELECT max(time) FROM %s group by app,function)"%tableName
        if function:
            where = where + " and function='%s'" % function
        sql_query=(
                      "SELECT @app:=app AS app, @function:=function AS function,"
                      "time,json_unquote(JSON_EXTRACT(report, '$.driver.inputs.cp_valid.uri')) AS uri,"
                      "JSON_EXTRACT(report, '$.driver.reports.sqlStatistics[0].total_items') AS total_items,"
                      "JSON_EXTRACT(report, '$.driver.reports.sqlStatistics') AS statistics "
                      "FROM  %s where %s"
                      " order by app,function,time;"
                  )% ( tableName,where)
        print (sql_query)
        try:
            self.db.execute("set @num := 0, @app := '', @function := '';")
            entries=self.db.query(sql_query)
            #calc_function_rowspan(entries)
            self.render("cpStatistics.html", items=entries, tag=env)
        except Exception,e:
            print(Exception)
            print(e)
            print("read sql error")
class pipelineHandler(BaseHandler):
    def get (self,env,app=None,function=None):
        limit = LIMIT_IN_FUNCTION_LIST if app and function else LIMIT_IN_APP_LIST if app else LIMIT_IN_FULL_LIST
        # print(env)
        # print(app)
        # print(function)
        suffix = "/%s/%s" % (app, function) if app and function else "/%s" % app if app else ""
        #env="stage03"
        tableName="report_"+env
        path="contentPipeline"
        where=""
        if app:
            where = where + " and app='%s'" % app
        if function:
            where = where + " and function='%s'" % function
        # print(where)
        # print(tableName)
        sql_query=(
                      "SELECT app,function,time,uri, "
                      "scrape_input_count,scrape_output_count,scrape_invalid_count,"
                      "cp_invalid_count,iibe_input_count,iibe_output_count,iibe_invalid_count,"
                      "dv_input_count,dv_output_count,dv_invalid_count "
                      " FROM ( "
                      "select time, uri, "
                      "scrape_input_count, scrape_output_count, "
                      "scrape_invalid_count,cp_invalid_count, "
                      "iibe_input_count,iibe_output_count,iibe_invalid_count,"
                      "dv_input_count, dv_output_count, dv_invalid_count, "
                      "@num:=IF(@app = app AND @function = function, @num + 1, 1) AS rank, "
                      "@app:=app AS app, "
                      "@function:=function AS function "
                      " from ( "
                      "SELECT  "
                      "app, "
                      "function, "
                      "MIN(time) AS `time`, "
                      "uri, "
                      "SUM(scrape_input_count) AS scrape_input_count, "
                      "SUM(scrape_output_count) AS scrape_output_count, "
                      "SUM(scrape_invalid_count) AS scrape_invalid_count, "
                      "SUM(cp_invalid_count) AS cp_invalid_count, "
                      "SUM(iibe_input_count) AS iibe_input_count, "
                      "SUM(iibe_output_count) AS iibe_output_count, "
                      "SUM(iibe_invalid_count) AS iibe_invalid_count, "
                      "SUM(dv_input_count) AS dv_input_count, "
                      "SUM(dv_output_count) AS dv_output_count, "
                      "SUM(dv_invalid_count) AS dv_invalid_count "
                      "FROM "
                      "((SELECT  "
                      "app, "
                      "function, "
                      "time, "
                      "JSON_EXTRACT(report, '$.driver.outputs.cpOutput.uri') AS uri, "
                      "JSON_EXTRACT(report, '$.driver.inputs.scrape_input.count') AS scrape_input_count, "
                      "JSON_EXTRACT(report, '$.driver.outputs.cpOutput.count') AS scrape_output_count, "
                      "JSON_EXTRACT(report, '$.driver.outputs.scrapeInvalidRecordsOutput.count') AS scrape_invalid_count, "
                      "JSON_EXTRACT(report, '$.driver.outputs.cpInvalidOutput.count') AS cp_invalid_count, "
                      "0 iibe_input_count, "
                      "0 iibe_output_count, "
                      "0 iibe_invalid_count, "
                      "0 dv_input_count, "
                      "0 dv_output_count, "
                      "0 dv_invalid_count "
                      "FROM "
                      " %s "
                      "WHERE "
                      "pipeline = 'contentPipeline' and JSON_EXTRACT(report, '$.driver.outputs.cpOutput.uri') not like '%%%%incremental%%%%'  %s ) UNION (SELECT  "
                      "app, "
                      "function, "
                      "time, "
                      "JSON_EXTRACT(report, '$.driver.inputs.vs_input.uri') AS uri, "
                      "0 scrape_input_count, "
                      "0 scrape_output_count, "
                      "0 scrape_invalid_count, "
                      "0 cp_invalid_count, "
                      "JSON_EXTRACT(report, '$.driver.inputs.vs_input.count') AS iibe_input_count, "
                      "JSON_EXTRACT(report, '$.driver.outputs.iibeOutput.count') AS iibe_output_count, "
                      "JSON_EXTRACT(report, '$.driver.outputs.iibeInvalidOutput.count') AS iibe_invalid_count, "
                      "0 dv_input_count, "
                      "0 dv_output_count, "
                      "0 dv_invalid_count "
                      ""
                      "FROM "
                      " %s "
                      "WHERE "
                      "pipeline = 'iibeEtlPipeline' and JSON_EXTRACT(report, '$.driver.inputs.vs_input.uri') not like '%%%%incremental%%%%'  %s ) UNION (SELECT "
                      "app, "
                      "function, "
                      "time, "
                      "JSON_EXTRACT(report, '$.driver.inputs.cp_input.uri'), "
                      "0 scrape_input_count, "
                      "0 scrape_output_count, "
                      "0 scrape_invalid_count, "
                      "0 cp_invalid_count, "
                      "0 iibe_input_count, "
                      "0 iibe_output_count, "
                      "0 iibe_invalid_count, "
                      "json_extract(report,'$.driver.inputs.cp_input.count') as dv_input_count, "
                      "json_extract(report,'$.driver.outputs.deepviewOutput.count') as dv_output_count, "
                      "json_extract(report,'$.driver.outputs.dvInvalidOutput.count') as dv_invalid_count "
                      ""
                      "FROM "
                      " %s "
                      "WHERE "
                      "pipeline = 'dvEtlPipeline' and JSON_EXTRACT(report, '$.driver.inputs.cp_input.uri') not like '%%%%incremental%%%%'"
                      " %s )) AS cp_summary "
                      "GROUP BY app , function , uri "
                      "ORDER BY app , function, time DESC "
                      ") AS vertical_summary )as fulltable where rank <= %d "
                      "; "
                  ) % (tableName, where, tableName, where, tableName, where,limit)
        print(sql_query)
        try:
            self.db.execute("set @num := 0, @app := '', @function := '';")
            entries=self.db.query(sql_query)
            # setFlag(entries)
            total = {}
            total['totalApp'] = {"1": 0, "2": 0, "3": 0}
            total['totalFunction'] = {"1": 0, "2": 0, "3": 0}
            setFlag(entries, total)
            self.render("pipeline.html", items=entries, tag=env, suffix=suffix, total=total)
        except Exception, e:
            print(Exception)
            print(e)
            print("read sql error")
class chartHandler(BaseHandler):
    def get(self, env,app=None,function=None):
        #env="stage03"
        tableName="report_"+env
        limit = LIMIT_IN_FUNCTION_LIST if app and function else LIMIT_IN_APP_LIST if app else LIMIT_IN_FULL_LIST
        suffix = "/%s/%s" % (app, function) if app and function else "/%s" % app if app else ""
        sql_query=(
                      "select app,function,group_concat(time) as time, "
                      "group_concat(scrape_input_count) as scrape_input_count,group_concat(scrape_output_count) as cp_input_count, "
                      "group_concat(scrape_invalid_count) as scrape_invalid_count,group_concat(cp_invalid_count) as cp_invalid_count,"
                      "group_concat(iibe_input_count) as iibe_input_count,group_concat(iibe_output_count) as iibe_output_count,group_concat(iibe_invalid_count) as iibe_invalid_count,"
                      "group_concat(dv_input_count) as dv_input_count, group_concat(dv_output_count) as dv_output_count, group_concat(dv_invalid_count) as dv_invalid_count"
                      " from ( "
                      "SELECT  "
                      "app, "
                      "function, "
                      "MIN(time) AS `time`, "
                      "uri, "
                      "SUM(scrape_input_count) AS scrape_input_count, "
                      "SUM(scrape_output_count) AS scrape_output_count, "
                      "SUM(scrape_invalid_count) AS scrape_invalid_count, "
                      "SUM(cp_invalid_count) AS cp_invalid_count, "
                      "SUM(iibe_input_count) AS iibe_input_count, "
                      "SUM(iibe_output_count) AS iibe_output_count, "
                      "SUM(iibe_invalid_count) AS iibe_invalid_count, "
                      "SUM(dv_input_count) AS dv_input_count, "
                      "SUM(dv_output_count) AS dv_output_count, "
                      "SUM(dv_invalid_count) AS dv_invalid_count "
                      "FROM "
                      "((SELECT  "
                      "app, "
                      "function, "
                      "time, "
                      "JSON_EXTRACT(report, '$.driver.outputs.cpOutput.uri') AS uri, "
                      "JSON_EXTRACT(report, '$.driver.inputs.scrape_input.count') AS scrape_input_count, "
                      "JSON_EXTRACT(report, '$.driver.outputs.cpOutput.count') AS scrape_output_count, "
                      "JSON_EXTRACT(report, '$.driver.outputs.scrapeInvalidRecordsOutput.count') AS scrape_invalid_count, "
                      "JSON_EXTRACT(report, '$.driver.outputs.cpInvalidOutput.count') AS cp_invalid_count, "
                      "0 iibe_input_count, "
                      "0 iibe_output_count, "
                      "0 iibe_invalid_count, "
                      "0 dv_input_count, "
                      "0 dv_output_count, "
                      "0 dv_invalid_count "
                      ""
                      "FROM "
                      " %s "
                      "WHERE "
                      "pipeline = 'contentPipeline' and JSON_EXTRACT(report, '$.driver.outputs.cpOutput.uri') not like '%%%%incremental%%%%' ) UNION (SELECT  "
                      "app, "
                      "function, "
                      "time, "
                      "JSON_EXTRACT(report, '$.driver.inputs.vs_input.uri') AS uri, "
                      "0 scrape_input_count, "
                      "0 scrape_output_count, "
                      "0 scrape_invalid_count, "
                      "0 cp_invalid_count, "
                      "JSON_EXTRACT(report, '$.driver.inputs.vs_input.count') AS iibe_input_count, "
                      "JSON_EXTRACT(report, '$.driver.outputs.iibeOutput.count') AS iibe_output_count, "
                      "JSON_EXTRACT(report, '$.driver.outputs.iibeInvalidOutput.count') AS iibe_invalid_count, "
                      "0 dv_input_count, "
                      "0 dv_output_count, "
                      "0 dv_invalid_count "
                      ""
                      "FROM "
                      " %s "
                      "WHERE "
                      "pipeline = 'iibeEtlPipeline' and JSON_EXTRACT(report, '$.driver.inputs.vs_input.uri') not like '%%%%incremental%%%%' ) UNION (SELECT "
                      "app, "
                      "function, "
                      "time, "
                      "JSON_EXTRACT(report, '$.driver.inputs.cp_input.uri'), "
                      "0 scrape_input_count, "
                      "0 scrape_output_count, "
                      "0 scrape_invalid_count, "
                      "0 cp_invalid_count, "
                      "0 iibe_input_count, "
                      "0 iibe_output_count, "
                      "0 iibe_invalid_count, "
                      "json_extract(report,'$.driver.inputs.cp_input.count') as dv_input_count, "
                      "json_extract(report,'$.driver.outputs.deepviewOutput.count') as dv_output_count, "
                      "json_extract(report,'$.driver.outputs.dvInvalidOutput.count') as dv_invalid_count "
                      ""
                      "FROM "
                      "%s "
                      "WHERE "
                      "pipeline = 'dvEtlPipeline' and JSON_EXTRACT(report, '$.driver.inputs.cp_input.uri') not like '%%%%incremental%%%%'"
                      " )) AS cp_summary "
                      "GROUP BY app , function , uri "
                      "ORDER BY app , function, time DESC "
                      ") AS vertical_summary group by app,function "
                      "; "
                  ) % ( tableName, tableName, tableName )
        print(sql_query)
        try:
            #self.db.execute("set @num := 0, @app := '', @function := '';")
            #self.db.execute("SET [SESSION | GLOBAL] group_concat_max_len = 15;")
            entries=self.db.query(sql_query)
            setFlag(entries)
            # entries = setFlag(entries)
            # print entries
            #calc_function_rowspan(entries)
            self.render("chart.html", items=entries, tag=env, suffix=suffix)
        except Exception, e:
            print(Exception)
            print(e)
            print("read sql error")

class PipelineJobHandler(BaseHandler):
    def get(self, env, pipeline, uri):
        #uri="\"oss://quixey-cp-stage/v4content/stage03/cp/book.qq.com/showBook/2016-07-07-05_08_03.475/cp/\""
        tableName="report_"+env
        if pipeline == "contentPipeline":
            where="JSON_EXTRACT(report, '$.driver.outputs.cpOutput.uri')"
        elif pipeline == "iibeEtlPipeline":
            where="JSON_EXTRACT(report, '$.driver.inputs.vs_input.uri')"
        elif pipeline == "dvEtlPipeline":
            where="JSON_EXTRACT(report, '$.driver.inputs.cp_input.uri')"
        sql_query=("select id, app, function, time, pipeline, report "
                   "from %s "
                   "where "
                   "pipeline = '%s'  and %s = %s;"
                   ) % ( tableName, pipeline, where, uri )
        print(sql_query)
        try:
            entries=self.db.query(sql_query)
            print(entries)
            # print(entries[0])
            if entries:
                for i in entries:
                    i["report"] = json.dumps(json.loads(i["report"]), indent=4, sort_keys=True)
            self.render("cp_report.html", items=entries, tag=env)
        except:
            print("read sql error")


def filter(entries):
    list = []
    now = datetime.datetime.now()
    print(entries)
    for index in entries:
        # jsonData = json.loads(index)
        time = index["time"]
        if (now -time).days < 14:
            print((now -time).days)
            list.append(index)
    return list


def setFlag(entries, total):
    list = []
    now = datetime.datetime.now()
    record = {}
    for index in entries:
        app = index['app']
        function = index['function']
        time = index['time']
        scrape_input = index['scrape_input_count']
        cpValid = scrape_input - index['cp_invalid_count']
        cpInvalid = index['cp_invalid_count']
        if (now - time).days > 7 or scrape_input == 0:
            record[app + '|' + function] = 3
            if not record.has_key(app) or record[app] <= 3:
                record[app] = 3
        elif cpValid / scrape_input < 0.9:
            record[app + '|' + function] = 2
            if not record.has_key(app) or record[app] <= 2:
                record[app] = 2
        else:
            record[app + '|' + function] = 1
            if not record.has_key(app) or record[app] <= 1:
                record[app] = 1

    app = ""
    for index in entries:
        index['flag'] = record[index['app']]
        index['funcFlag'] = record[index['app'] + '|' + index['function']]
        flag = str(index['flag'])
        funcFlag = str(index['funcFlag'])
        if index['app'] != app:
            total['totalApp'][flag] += 1
            app = index['app']
        total['totalFunction'][funcFlag] += 1
    total['totalApp']['count'] = total['totalApp']['1'] + total['totalApp']['2'] + total['totalApp']['3']
    total['totalFunction']['count'] = total['totalFunction']['1'] + total['totalFunction']['2'] + total['totalFunction']['3']
    return list






def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port, address=options.host)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
