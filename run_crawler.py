from UnicomCrawlerRequests import UnicomCrawlerRequests
from UnicomCrawlerSelenium import UnicomCrawler
from UnicomExcelProcessing import ExcelProcessing

c = UnicomCrawlerRequests()
c.full_run()
e = ExcelProcessing()
e.full_run()
