# -*- coding: utf-8 -*-
import re
import urllib
import urllib2
import time

# 通过url获取网站源码
def getHtml(url):
    print url
    page = urllib2.urlopen(url)
    html = page.read()
    return html

#在html中找到匹配的url
def getImage(html):
    reg = r'src="(http://.+?\.jpg)" '
    image = re.compile(reg)
    imageList = re.findall(image, html)
    i = 0
    for imageUrl in imageList:
        print imageUrl
        #下载文件到本地
        urllib.urlretrieve(imageUrl, '%s.jpg'%time.time() )
        i += 1
    return imageList


url = "http://tieba.baidu.com/p/2772656630"
html = getHtml(url)
print getImage(html)
# print time.time


