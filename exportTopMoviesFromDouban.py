#!/usr/bin/env python
#! encoding=utf-8

# Author        : kesalin@gmail.com
# Blog          : http://kesalin.github.io
# Date          : 2016/07/13
# Description   : 抓取豆瓣上指定标签的电影并导出为 Markdown 文件，多线程版本. 
# Version       : 1.0.0.0
# Python Version: Python 2.7.3
# Python Queue  : https://docs.python.org/2/library/queue.html
# Beautiful Soup: http://beautifulsoup.readthedocs.io/zh_CN/v4.4.0/#

import os
import time
import timeit
import datetime
import re
import string
import urllib2
import math

from threading import Thread
from Queue import Queue
from bs4 import BeautifulSoup

gHeader = {"User-Agent": "Mozilla-Firefox5.0"}

# 电影信息类
class ItemInfo:
    name = ''
    url = ''
    icon = ''
    ratingNum = 0.0
    ratingPeople = 0
    comment = ''
    compositeRating = 0.0

    def __init__(self, name, url, icon, num, people, comment):
        self.name = name
        self.url = url
        self.icon = icon
        self.ratingNum = num
        self.ratingPeople = people
        self.comment = comment
        self.compositeRating = num

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        if self.url == other.url:
            return True
        return False

    def __sortByCompositeRating(self, other):
        val = self.compositeRating - other.compositeRating
        if val < 0:
            return 1
        elif val > 0:
            return -1
        else:
            val = self.ratingPeople - other.ratingPeople
            if val < 0:
                return 1
            elif val > 0:
                return -1
            else:
                return val

    def __cmp__(self, other):
        return self.__sortByCompositeRating(other)

# 获取 url 内容
def getHtml(url):
    try :
        request = urllib2.Request(url, None, gHeader)
        response = urllib2.urlopen(request)
        data = response.read().decode('utf-8')
        return data
    except urllib2.URLError, e :
        if hasattr(e, "code"):
            print "The server couldn't fulfill the request: " + url
            print "Error code: %s" % e.code
        elif hasattr(e, "reason"):
            print "We failed to reach a server. Please check your url: " + url + ", and read the Reason."
            print "Reason: %s" % e.reason
    return None

# 导出为 Markdown 格式文件
def exportToMarkdown(tag, items, total):
    path = "{0}.md".format(tag)
    if(os.path.isfile(path)):
        os.remove(path)

    today = datetime.datetime.now()
    todayStr = today.strftime('%Y-%m-%d %H:%M:%S %z')
    file = open(path, 'a')
    file.write('## 说明\n\n')
    file.write(' > 本页面是由 Python 爬虫根据电影推荐算法抓取豆瓣电影信息自动生成，列出特定主题排名靠前的一百或两百多部电影。  \n\n')
    file.write(' > 我使用的推荐算法似乎要比豆瓣默认的算法要可靠些，我可以根据特定主题对推荐算法进行调整。大家可以访问 ' 
        '[豆瓣电影爬虫](https://github.com/luozhaohui/PythonSnippet/blob/master/exportTopMoviesFromDouban.py) 查看推荐算法。'
        '希望能得到大家的反馈与建议，改善算法，提供更精准的电影排名。  \n\n')
    file.write(' > 联系方式：  \n')
    file.write('    + 邮箱：kesalin@gmail.com  \n')
    file.write('    + 微博：[飘飘白云](http://weibo.com/kesalin)  \n')

    file.write('\n## {0} Top {1} 电影\n\n'.format(tag, len(items)))
    file.write('### 总共分析了 {0} 部电影，更新时间：{1}\n'.format(total, todayStr))

    i = 0
    for book in items:
        file.write('\n### No.{0:d} {1}\n'.format(i + 1, book.name))
        file.write(' > **电影名称**： [{0}]({1})  \n'.format(book.name, book.url))
        file.write(' > **豆瓣链接**： [{0}]({1})  \n'.format(book.url, book.url))
        file.write(' > **发行信息**： {0}  \n'.format(book.comment))
        file.write(' > **豆瓣评分**： {0}  \n'.format(book.ratingNum))
        if book.ratingPeople < 0:
            file.write(' > **评分人数**： 尚未上映  \n')
        else:
            file.write(' > **评分人数**： {0} 人  \n'.format(book.ratingPeople))
        i = i + 1
    file.close()

# 解析图书信息
def parseItemInfo(tag, minNum, maxNum, k, page, itemInfos):
    soup = BeautifulSoup(page, 'html.parser')
    items = soup.find_all("tr", "item")
    for item in items:
        #print item.prettify().encode('utf-8')

        # get name & url & description
        itemName = ''
        itemUrl = ''
        description = ''
        content = item.find("div", "pl2")
        if content != None:
            href = content.find("a")
            if href != None:
                #print href.prettify().encode('utf-8')
                itemUrl = href['href'].encode('utf-8')
                contents = href.contents
                if contents != None:
                    itemName = contents[0].strip().encode('utf-8')
                    itemName = itemName.replace('\n',' ').replace(' ', '').replace('/', ' / ')
                span = href.find("span")
                if span != None and span.string != None:
                    subTitle = span.string.strip().encode('utf-8')
                    itemName = '{0}{1}'.format(itemName, subTitle)

            des = content.find("p", 'pl')
            if des != None and des.string != None:
                description = des.string.strip().encode('utf-8')

        # print " > name: {0}".format(itemName)
        # print " > itemUrl: {0}".format(itemUrl)
        # print " > description: {0}".format(description)

        # get url and image
        itemImage = ''
        content = item.find("img")
        if content != None:
            itemImage = content['src'].encode('utf-8')
        #print " > image: {0}".format(itemImage)

        # get rating
        ratingNum = 0.0
        ratingPeople = 0
        content = item.find("span", "rating_nums")
        if content != None and content.string != None:
            ratingStr = content.string.strip().encode('utf-8')
            if len(ratingStr) > 0:
                ratingNum = float(ratingStr)
        content = item.find("span", "pl")
        if content != None:
            ratingStr = content.string.strip().encode('utf-8')
            if ratingStr == '(尚未上映)':
                ratingPeople = -1
            else:
                pattern = re.compile(r'(\()([0-9]*)(.*)(\))')
                match = pattern.search(ratingStr)
                if match:
                    ratingStr = match.group(2).strip()
                    if len(ratingStr) > 0:
                        ratingPeople = int(ratingStr)
        #print " > ratingNum: {0}, ratingPeople: {1}".format(ratingNum, ratingPeople)

        # add imte info to list
        itemInfo = ItemInfo(itemName, itemUrl, itemImage, ratingNum, ratingPeople, description)
        itemInfo.compositeRating = computeCompositeRating(tag, minNum, maxNum, k, ratingNum, ratingPeople)
        itemInfos.append(itemInfo)

#=============================================================================
# 生产者-消费者模型
#=============================================================================
class Producer(Thread):
    url = ''
    
    def __init__(self, t_name, url, queue):  
        Thread.__init__(self, name=t_name)
        self.url = url
        self.queue = queue

    def run(self):
        page = getHtml(self.url)
        if page != None:
            # block util a free slot available
            self.queue.put(page, True)

class Consumer(Thread):
    running = True
    tag = ''
    items = []
    queue = None
    minNum = 5
    maxNum = 5000
    k = 0.25

    def __init__(self, t_name, tag, minNum, maxNum, k, queue, items):  
        Thread.__init__(self, name=t_name)
        self.queue = queue
        self.items = items
        self.tag = tag
        self.minNum = max(10, min(200, minNum))
        self.maxNum = max(1000, min(maxNum, 20000))
        self.k = max(0.01, min(1.0, k))

    def stop(self):
        self.running = False

    def run(self):
        while True:
            if self.running == False and self.queue.empty():
                break;

            page = self.queue.get()
            if page != None:
                parseItemInfo(self.tag, self.minNum, self.maxNum, self.k, page, self.items)
            self.queue.task_done()
 

def spider(tag, minNum, maxNum, k):
    print '   抓取 [{0}] 电影 ...'.format(tag)
    start = timeit.default_timer()

    # all producers
    queue = Queue(20)
    itemInfos = []
    producers = []

    # get first page of doulist
    url = "https://movie.douban.com/tag/{0}".format(tag)
    page = getHtml(url)
    if page == None:
        print ' > invalid url {0}'.format(url)
    else:
        # get url of other pages in doulist
        soup = BeautifulSoup(page, 'html.parser')
        content = soup.find("div", "paginator")
        #print content.prettify().encode('utf-8')

        nextPageStart = 100000
        lastPageStart = 0
        for child in content.children:
            if child.name == 'a':
                pattern = re.compile(r'(start=)([0-9]*)(.*)(&type=)')
                match = pattern.search(child['href'].encode('utf-8'))
                if match:
                    index = int(match.group(2))
                    if nextPageStart > index:
                        nextPageStart = index
                    if lastPageStart < index:
                        lastPageStart = index

        # process current page
        #print " > process page : {0}".format(url)
        queue.put(page)

        # create consumer
        consumer = Consumer('Consumer', tag, minNum, maxNum, k, queue, itemInfos)
        consumer.start()

        # create producers
        producers = []
        for pageStart in range(nextPageStart, lastPageStart + nextPageStart, nextPageStart):
            pageUrl = "{0}?start={1:d}&type=T".format(url, pageStart)
            producer = Producer('Producer_{0:d}'.format(pageStart), pageUrl, queue)
            producer.start()
            producers.append(producer)
            #print " > process page : {0}".format(pageUrl)
            time.sleep(0.1)         # slow down a little

        # wait for all producers
        for producer in producers:
            producer.join()

        # wait for consumer
        consumer.stop()
        queue.put(None)
        consumer.join()

        # summrise
        total = len(itemInfos)
        elapsed = timeit.default_timer() - start
        print "   获取 %d 部 [%s] 电影信息，耗时 %.2f 秒"%(total, tag, elapsed)
        return itemInfos


def process(tags):
    tagList = tags[0].split(',')
    minNum = tags[1]
    maxNum = tags[2]
    k = tags[3]
    outputNum = max(100, tags[4])

    items = []
    # spider
    for tag in tagList:
        tagItems = spider(tag.strip(), minNum, maxNum, k)
        items = list(set(items + tagItems))

    total = len(items)
    print " > 共获取 {0} 部 [{1}] 不重复电影信息".format(total, tags[0])

    # sort
    items = sorted(items)
    # get top 100
    if len(items) > outputNum:
        items = items[0:outputNum]

    # export to markdown
    exportToMarkdown(tagList[0], items, total)

#=============================================================================
# 排序算法
#=============================================================================
def computeCompositeRating(tag, minNum, maxNum, k, num, people):
    people = max(1, min(maxNum, people))
    if people <= minNum:
        people = minNum / 3
    peopleWeight = math.pow(people, k)
    if people < 200:
        return (num * 40 + peopleWeight * 60) / 100.0
    elif people < 500:
        return (num * 50 + peopleWeight * 50) / 100.0
    elif people < 1000:
        return (num * 60 + peopleWeight * 40) / 100.0
    elif people < 5000:
        return (num * 70 + peopleWeight * 30) / 100.0
    elif people < 10000:
        return (num * 80 + peopleWeight * 20) / 100.0
    else:
        return (num * 90 + peopleWeight * 10) / 100.0

#=============================================================================
# 程序入口：抓取指定标签的书籍
#=============================================================================
if __name__ == '__main__': 
    tags = [
        # ["经典", 100, 50000, 0.25, 300],
        # ["剧情,感人", 100, 50000, 0.25, 250],
        # ["励志", 100, 50000, 0.25, 200],
        # ["喜剧", 100, 50000, 0.25, 300],
        # ["搞笑", 100, 50000, 0.25, 300],
        # ["爱情,情色,浪漫", 100, 50000, 0.25, 250],
        # ["科幻,魔幻", 100, 50000, 0.25, 150],
        # ["动作,暴力", 100, 50000, 0.25, 200],
        # ["史诗", 100, 50000, 0.25, 100],
        # ["战争", 100, 50000, 0.25, 200],
        # ["悬疑", 100, 50000, 0.25, 200],
        # ["犯罪,黑帮", 100, 50000, 0.25, 200],
        # ["恐怖,惊悚", 100, 50000, 0.25, 200],
        # ["青春", 100, 50000, 0.25, 200],
        # ["文艺", 100, 50000, 0.25, 200],
        # ["童话,童年", 100, 50000, 0.25, 200],
        # ["纪录片,传记", 100, 50000, 0.25, 300],
        # ["黑色幽默", 100, 50000, 0.25, 200],
        # ["亚洲,日本,韩国,印度,泰国,新加坡", 100, 50000, 0.25, 300],
        # ["欧美,美国,加拿大,欧洲,德国,英国,法国,意大利,西班牙,澳大利亚,俄罗斯,伊朗,巴西,瑞典,丹麦,波兰,捷克,比利时,墨西哥,土耳其", 100, 50000, 0.25, 300],
        # ["中国,中国大陆,内地", 100, 50000, 0.25, 300],
        # ["香港", 100, 50000, 0.25, 300],
        # ["台湾", 100, 50000, 0.25, 200],
        # ["美国", 100, 50000, 0.25, 300],
        # ["英国", 100, 50000, 0.25, 200],
        # ["法国", 100, 50000, 0.25, 200],
        ["日本", 100, 50000, 0.25, 300],
        # ["韩国", 100, 50000, 0.25, 200],
    ]

    start = timeit.default_timer()

    for tag in tags:
        process(tag)

    elapsed = timeit.default_timer() - start
    print "== 总耗时 %.2f 秒 =="%(elapsed)