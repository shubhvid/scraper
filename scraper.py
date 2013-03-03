###############################################
# March 3, 2013
#
# Authors:
# 1. Shubham Vidyarthi
# URL: http://www.svidyarthi.com
# Email: shubhvid@gmail.com
#
###############################################





import sys
import os
import re
from Queue import Queue
import threading
import urllib2
from bs4 import BeautifulSoup

DEBUG = False
rpmDict_lock = threading.Lock()
urlQueue = Queue()  # already synchronized
rpmDict = {}

def debug(msg):
    if DEBUG:
        print "DEBUG: %s" % msg


class Worker (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True   

    def run(self):
        while True:
            try:
                url = urlQueue.get()
                urlf = None
                try:
                    urlf = urllib2.urlopen(url)
                    page = urlf.read()
                    
                except urllib2.HTTPError, e:
                    debug("%s: page %s cannot be loaded" % (self.name, url))
                    continue
                finally:
                    if urlf:
                        urlf.close()
                soup = BeautifulSoup(page)
                for link in soup.find_all('a'):
                    href = link.get('href')
                    if href.startswith('?') or href.startswith('/'): # parent directories should be ignored
                        continue
                    if href.endswith('/'):
                        debug ("%s: %s" % (self.name, href))
                        urlQueue.put(url + href)
                    else:
                        with rpmDict_lock:
                            rpmDict[href] = url
            finally:
                urlQueue.task_done()

        

class Scraper:
    def __init__(self, url=None, outfile=None, workerThreads = 20):
        self.url = url
        self.outfile = outfile
        self.workerThreads = workerThreads
    
    def printUsage(self):
        print "\nUSAGE: "
        print "%s --help\n" % sys.argv[0]
        print "%s -u <url> -o output_file\n" % sys.argv[0]
        sys.exit(1)

    def parseCommandOptions(self, args):
        #--------------------------------------
        #  Parse args[] by iterating over it
        #--------------------------------------
        
        while args:
            arg = args[0] # This arg
            del args[0]
            
            try:
                if arg[0] == '-' or arg == "/?":
                    if arg.lower() in ['--url', '-u', '-url']:
                        self.url = args[0].strip()
                        if not self.url.endswith('/'):
                            self.url = self.url + '/'
                        del args[0]
                    
                    elif arg.lower() in ["-o", "--outfile", "-outfile", "--out", "-out"]:
                        self.outfile = args[0].strip()
                        del args[0]
                    
                    elif arg.lower() in ["-h", "--help", "/?"]:
                        printUsage()
                    
                    else:
                        fatal("Invalid argument %s" % arg)
            
            except IndexError:
                error("Missing command line options after %s" % arg)
                printUsage()
    
    def main(self):
        args = sys.argv[1:]
        self.parseCommandOptions(args)
        debug("URL: %s" % self.url)
        debug("Output File: %s" % os.path.abspath(self.outfile))
        for i in range(self.workerThreads):
            wt = Worker()
            wt.name = "worker%s" % i
            wt.start()
        urlQueue.put(self.url)
        urlQueue.join()
        rpms = rpmDict.keys()
        rpms.sort()
        f = None
        try:
            f = open(self.outfile + ".html", 'w')
            for k in rpms:
                f.write('<HTML><BODY>\n')
                f.write("<a href=\"" + rpmDict[k]+k + "\">" + k + "</a><br/>\n")
                f.write('</BODY></HTML>')
        finally:
            if f:
                f.close()


if __name__ == "__main__":
    scraper = Scraper()
    scraper.main()