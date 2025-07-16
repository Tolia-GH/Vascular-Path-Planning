import cv2
import numpy as np

class RegionalGrowth:
    def __init__(self,imgPath):
        self.imgPath=imgPath

    def zh_cn(self,string):
        return string.encode("gbk").decode('UTF-8', errors='ignore')

    def showImg(self):
        #显示图片
        img=cv2.imread(self.imgPath)
        print(type(img.shape))
        window_name = self.zh_cn('图')
        cv2.namedWindow(window_name, 0)  # 为窗口定义名字
        cv2.resizeWindow(window_name, 736, 416)  # 设置窗口显示的大小：W、H
        cv2.imshow(window_name, img)  # 显示窗口的名字， 所要显示的图片
        cv2.waitKey(0)  # 等待参数为毫秒，参数为 0表示 无限等待
        cv2.destroyAllWindows()
    def showGrayImg(self):
        # 显示图片
        img = cv2.imread(self.imgPath)
        grayImg = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)  # 灰度图Gray=0.299*R+0.587*G+0.114*B
        window_name ='CT'
        cv2.namedWindow(window_name, 0)  # 为窗口定义名字
        cv2.resizeWindow(window_name, 736, 416)  # 设置窗口显示的大小：W、H
        cv2.imshow(window_name, grayImg )  # 显示窗口的名字， 所要显示的图片
        cv2.imwrite(r'./images/ctgray.jpg',grayImg)
        cv2.waitKey(0)  # 等待参数为毫秒，参数为 0表示 无限等待
        cv2.destroyAllWindows()
        return grayImg

    def meanDiff(self,grayImg,seedMark):
        #计算同一区域的平均值与邻域的像素点之差
        areaGrayImg=np.multiply(grayImg,seedMark)#同位置元素相乘
        # areaSum=np.sum(areaGrayImg)
        # count=np.count_nonzero(areaGrayImg == 0)
        # meanArea=areaSum/count
        #或者直接使用np.mean
        meanArea=np.mean(areaGrayImg)
        return meanArea


    def regional_growth (self,grayImg,seeds,threshold=15,kind=0):#种子点与遍历点像素值之差小于某个阈值归并为同一区域
        # 每次区域生长的时候的种子像素之间的八个邻接点
        # connects = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1),(0, 1), (-1, 1), (-1, 0)]
        connects = [ (0, -1), (1, 0), (0, 1), (-1, 0)]#4邻域
        height, weight = grayImg.shape  #得到图片像素的高与宽
        seedMark = np.zeros(grayImg.shape)#初始化全为0，用来标记同一个区域
        print(seedMark)
        seedList = []
        for seed in seeds:
            seedList.append(seed)
        #选取种子开始生长，直到没有可以生长的种子
        while(len(seedList)>0):
            #出栈一个种子
            currentPoint=seedList.pop()
            #并将生长点对应seedMark点赋值1
            seedMark[currentPoint[0],currentPoint[1]]=1
            # 以种子点为中心，八邻域的像素进行比较
            for i in range(4):#0~7
                tmpX = currentPoint[0] + connects[i][0]
                tmpY = currentPoint[1] + connects[i][1]
                # 判断是否为图像外的点，若是则跳过。  如果种子点是图像的边界点，邻域点就会落在图像外
                if tmpX < 0 or tmpY < 0 or tmpX >= height or tmpY >= weight:
                    continue
                # 判断邻域点和种子点的差值
                if seedMark[tmpX, tmpY] == 0:  #如果邻域点还未划分过
                    if kind==0:
                        grayDiff = abs(int(grayImg[tmpX][tmpY])-int(grayImg[currentPoint[0]][currentPoint[1]]))
                    if kind==1:
                        grayDiff=abs(int(grayImg[tmpX][tmpY])-int(self.meanDiff(grayImg,seedMark))) #算区域内的平均值与领域点的差
                # 归类
                # 并作为下一个种子点放入seedList
                    if grayDiff <= threshold:
                        seedMark[tmpX, tmpY] = 1
                        seedList.append((tmpX, tmpY))
        return seedMark

if __name__ == '__main__':
    imgpath='./images/blue.jpg'
    rg=RegionalGrowth(imgpath)
    grayImg=rg.showGrayImg()
    seeds = [(973,996)]#初始种子
    seedMarkBinary=rg.regional_growth(grayImg,seeds,2,0)#0表示使用种子点与邻域点比较，1表示选用区域平均值与邻域点比较
    window_name = 'segment'
    cv2.namedWindow(window_name, 0)  # 为窗口定义名字
    cv2.resizeWindow(window_name, 736, 416)  # 设置窗口显示的大小：W、H
    cv2.imshow(window_name, seedMarkBinary)#其中0 – 表示黑色, 1 – 表示白色
    cv2.waitKey(0)
    cv2.destroyAllWindows()