# 瑞鈊SDK开发说明文档
Windows C++版

- 版本号：V1.0.2
- 型号规格：RUIXIN SDK
- 艾瑞迈迪医疗科技（北京）有限公司

## 目录

- 1. 简介 (4)
- 1.1 产品概述 (4)
- 1.2 环境要求 (4)
- 1.2.1 系统要求 (4)
- 1.2.2 开发环境与编译语言 (4)
- 2. SDK接口说明 (4)
- 2.1 设备扫描接口 (4)
- 2.1.1 getDeviceInfo (4)
- 2.1.2 updateDeviceInfo (4)
- 2.2 设备连接接口 (5)
- 2.2.1 connect (5)
- 2.2.2 disconnect (5)
- 2.2.3 getDeviceVersion (5)
- 2.2.3 getAPIVersion (6)
- 2.4 数据传输接口 (6)
- 2.4.1 startTracking (6)
- 2.4.2 stopTracking (7)
- 2.4.3 trackingUpdate (7)
- 2.4.4 getTrackingData (7)
- 2.5 状态监测接口 (7)
- 2.5.1 getConnectionStatus (8)
- 2.5.2 getSensorConnected (8)
- 2.6 常用工具接口 (8)
- 2.6.1 pivotTipCalibration (8)
- 2.6.2 fixedDirCalibration (9)
- 2.6.3 getNetAdaptorInfo (10)
- 3. SDK重要数据结构 (10)
- 3.1 跟踪信息数据结构SensorToolTrackingData (10)
- 3.2 跟踪位姿信息数据结构Transformation (10)
- 3.8 网卡信息数据结构SensorNetAdaptorInfo (11)
- 4. SDK重要枚举类型的命名空间 (11)
- 4.1 设备连接状态SensorConnectionStatus (11)
- 4.7 器械标定状态SensorCalibrationAlert (11)
- 4.8 器械跟踪状态SensorTransformationStatus (12)
- 5. Demo使用指南 (12)
- 5.1 连接准备 (12)
- 5.2 文件目录 (12)
- 5.3 使用流程 (12)
- 5.5 调用流程 (12)
- 6. 常见问题 (13)

## 1. 简介

### 1.1 产品概述
适用于瑞鈊系列产品的SDK工具包，包含瑞鈊的连接与初始化、传感器定位及指令控制等功能，用户可根据业务需求结合SDK灵活的进行应用层开发。

### 1.2 环境要求

#### 1.2.1 系统要求
Windows 10/11系统

#### 1.2.2 开发环境与编译语言
Visual Studio 2013/2015/2017/2019/2022，C++

## 2. SDK接口说明

### 2.1 设备扫描接口
相关头文件SensorDeviceScan.h。

#### 2.1.1 getDeviceInfo

**原型**

```cpp
std::map<std::string, std::string> getDeviceInfo();
```

**功能描述**
获取可连接设备的hostname与IP地址。

**参数**
无。

**返回值**
std::map<std::string, std::string>类型：map容器储存了所有可连接设备的hostname与IP地址，其中键为设备hostname，值为设备IP地址。

#### 2.1.2 updateDeviceInfo

**原型**

```cpp
void updateDeviceInfo();
```

**功能描述**
刷新当前所有可连接设备的hostname与IP地址。

**参数**
无。

**返回值**
无。

### 2.2 设备连接接口
相关头文件SenSorCombinedAPI.h。

#### 2.2.1 connect

**原型**

```cpp
int connect(std::string hostname, bool errorPrint = false);
```

**功能描述**
连接与初始化设备。

**参数**
std::string类型：设备对应的hostname或IP；
bool类型：设置打印/不打印连接通讯错误信息，默认不打印。

**返回值**
int类型：连接设备成功或失败状态值，其中-1对应"连接失败"，0对应"连接成功"。

#### 2.2.2 disconnect

**原型**

```cpp
void disconnect();
```

**功能描述**
断开与设备的连接。

**参数**
无。

**返回值**
无。

#### 2.2.3 getDeviceVersion

**原型**

```cpp
std::vector<int> getDeviceVersion ();
```

**功能描述**
返回设备名称与固件版本号。

**参数**
无。

**返回值**
std::vector<int>类型：vector容器第一位存储了设备名称，后三位储存了固件版本号。

#### 2.2.3 getAPIVersion

**原型**

```cpp
std::vector<int> getAPIVersion ();
```

**功能描述**
返回sdk版本号。

**参数**
无。

**返回值**
std::vector<int>类型：vector容器储存了三位数字，代表sdk版本号。

#### 2.2.4 getTransmitterID

**原型**

```cpp
std::string getTransmitterID ();
```

**功能描述**
返回发射器ID。

**参数**
无。

**返回值**
std::string类型：代表发射器的ID。

### 2.4 数据传输接口
相关头文件ARMDCombinedAPI.h。

#### 2.4.1 startTracking

**原型**

```cpp
void startTracking();
```

**功能描述**
开始跟踪传感器。

**参数**
无。

**返回值**
无。

#### 2.4.2 stopTracking

**原型**

```cpp
void stopTracking();
```

**功能描述**
停止跟踪传感器。

**参数**
无。

**返回值**
无。

#### 2.4.3 trackingUpdate

**原型**

```cpp
void trackingUpdate();
```

**功能描述**
刷新所有传感器的跟踪数据。

**参数**
无。

**返回值**
无。

#### 2.4.4 getTrackingData

**原型**

```cpp
std::vector<SensorToolTrackingData>getTrackingData();
```

**功能描述**
获取当前所有传感器的跟踪数据。

**参数**
无。

**返回值**
std::vector< SensorToolTrackingData >类型：vector容器储存了当前所有传感器的跟踪数据SensorToolTrackingData。

### 2.5 状态监测接口
相关头文件ARMDCombinedAPI.h。

#### 2.5.1 getConnectionStatus

**原型**

```cpp
uint16_t getConnectionStatus();
```

**功能描述**
获取当前设备连接状态。

**参数**
无。

**返回值**
uint16_t类型：当前设备连接状态，其枚举类型命名空间为SensorConnectionStatus。

#### 2.5.2 getSensorConnected

**原型**

```cpp
bool getSensorConnected(int id);
```

**功能描述**
获取指定传感器的连接状态。

**参数**
无。

**返回值**
bool类型：当前传感器连接状态，true:连接正常，false:连接失败。

### 2.6 常用工具接口
相关头文件ARMDCombinedAPI.h。

#### 2.6.1 pivotTipCalibration

**原型1**

```cpp
uint16_t pivotTipCalibration(std::vector<std::vector<double>> rot,
std::vector<std::vector<double>> tran, std::vector<double>& tip, double& error);
```

**功能描述**
根据器械绕尖端点转动的跟踪数据标定其在自身坐标系下的尖端坐标。

**参数**
std::vector<std::vector<double>>类型：跟踪数据的旋转矩阵3n*3，其中n为跟踪数据的数量；
std::vector<std::vector<double>>类型：跟踪数据的平移向量3n*1，其中n为跟踪数据的数量；
std::vector<double>&类型：用于存储标定结果，即器械在其自身坐标系下的尖端坐标，若标定失败，返回空白vector容器；
double&类型：用于存储标定误差，若标定失败，返回-1。

**返回值**
uint16_t类型：标定成功与否状态，其枚举类型命名空间为CalibrationAlert。

**原型2**

```cpp
uint16_t pivotTipCalibration(ToolCalibrationData& tool, std::vector<ToolTrackingData>
trackingdataVect, std::vector<double>& tip, std::vector<double>& offset, double& error, bool
update = false);
```

**功能描述**
根据器械绕尖端点转动的跟踪数据标定其尖端。

**参数**
ToolCalibrationData&类型：待标定的器械数据；
std::vector<ToolTrackingData>类型：器械转动过程中采集的跟踪数据；
std::vector<double>&类型：用于存储标定结果，即器械在其自身坐标系下的尖端坐标，若标定失败，返回空白vector容器；
std::vector<double>&类型：用于存储当前标定与上次标定结果间在器械自身坐标系下x，y，z方向上的偏差，若标定失败，返回空白vector容器；
double&类型：用于存储标定误差，若标定失败，返回-1；
bool类型：是否更新输入待标定的器械数据中尖端坐标信息，默认为false。

**返回值**
uint16_t类型：标定成功与否状态，其枚举类型命名空间为CalibrationAlert。

#### 2.6.2 fixedDirCalibration

```cpp
uint16_t fixedDirCalibration(SensorToolTrackingData trackingdata, double pt1[3],
double pt2[3], std::vector<double>& dir );
```

**功能描述**
根据器械的当前跟踪数据与瑞鈊坐标系下方向向量标定其在自身坐标系下的方向向量(基于探针方向标定，使用探针沿着某一个方向分别采集两个点确认该探针的方向，第一次采集需要记录：探针当前的跟踪数据及探针尖端坐标；第二次采集需要记录：探针尖端坐标即可)。

**参数**
SensorToolTrackingData &类型：器械当前跟踪数据；
double[3]类型：瑞鈊坐标系下探针尖端点坐标；
double[3]类型：瑞鈊坐标系下探针尖端点坐标；
std::vector<double>&类型：用于存储标定结果，即器械在其自身坐标系下的方向向量，若标定失败，返回空白vector容器；

**返回值**
uint16_t类型：标定成功与否状态，其枚举类型命名空间为CalibrationAlert。

#### 2.6.3 getNetAdaptorInfo

**原型**

```cpp
NetAdaptorInfo getNetAdaptorInfo();
```

**功能描述**
获取与设备连接的网卡信息。

**参数**
无。

**返回值**
NetAdaptorInfo类型：网卡信息，包括网卡的名称、连接类型、网速、连接状态，其中，网速单位：MB/s。注意：NetAdaptorInfo类型的连接状态可以用于监测瑞鈊设备的断连情况，当值为false时，瑞鈊设备断开，其监测响应速度快于getConnectionStatus函数。

## 3. SDK重要数据结构

### 3.1 跟踪信息数据结构SensorToolTrackingData

```cpp
struct SensorToolTrackingData
{
std::string name = ""; //名称
std::string timespec = ""; //当前时间
int connectStatus = 0; //连接状态
SensorTransformation transform; //位姿信息
}
```

### 3.2 跟踪位姿信息数据结构Transformation

```cpp
struct Transformation
{
uint16_t status; //匹配状态 ，其枚举类型命名空间为
SensorTransformationStatus
double matrix[4][4]; //姿态矩阵
double qw, qx, qy, qz; //姿态四元数
double tx, ty, tz; //器械尖端坐标
double yaw, pitch, roll; //器械旋转角度
Transformation inversed(); //计算姿态逆矩阵
};
```

### 3.8 网卡信息数据结构SensorNetAdaptorInfo

```cpp
struct SensorNetAdaptorInfo
{
std::string name = ""; //设备连接的网卡名称
std::string IP = ""; //设备连接的IP
std::string MAC = ""; //设备连接的Mac地址
std::string connectionType = ""; //设备连接的网卡连接类型
int speed = 0; //设备连接的网卡网速
bool linked = false; //设备连接的网卡连接状态
};
```

## 4. SDK重要枚举类型的命名空间

### 4.1 设备连接状态SensorConnectionStatus

```cpp
namespace SensorConnectionStatus
{
enum value
{
Connected = 0x0000, //连接成功
DisConnected = 0x0001, //断开成功
DisConnectedFailed = 0x0002, //断开失败
PortConflicts = 0x0003, //连接失败，连接端口冲突
ResloveError = 0x0004, //连接失败，IP解析错误
InitialUDPError = 0x0005, //连接失败，初始化错误
Interruption = 0x0006, //连接中断
InvalidAddr = 0x0007, //连接失败，IP地址无效
DeviceInexist = 0x0008, //连接失败，设备不存在
TimeOut = 0x0009, //连接失败，设备连接超时
UnknownError = 0x000A, //连接失败，未知错误
};
}
```

### 4.7 器械标定状态SensorCalibrationAlert

```cpp
namespace SensorCalibrationAlert
{
enum value
{
Normal = 0x0000, //标定成功
AbnormalData = 0x0001, //标定失败，输入的器械跟踪数据异常
InadequateData = 0x0002, //标定失败，输入的器械跟踪数据不足
ComputationError = 0x0003, //标定失败，标定过程计算异常
};
}
```

### 4.8 器械跟踪状态SensorTransformationStatus

```cpp
namespace SensorTransformationStatus
{
enum values
{
Enabled = 0x0000, //传感器跟踪成功
OutOfVolume = 0x0001, //传感器跟踪成功，但传感器超出范围
ToolMissing = 0x0009, //传感器跟踪失败
};
}
```

## 5. Demo使用指南
测试该Demo的系统为Window 10，开发环境为Visual Studio 2013/2015/2017/2019/2022。

### 5.1 连接准备
接入瑞鈊设备，确认设备背面标记的hostname，例如RX-PM000000.local。

### 5.2 文件目录
include文件夹包含SDK头文件（*.h），lib文件夹包含SDK库文件（RuixinSDK.lib或RuixinSDKd.lib），配置库gsl包含include文件夹与lib文件夹（应用于内部计算应用），调用SDK的示例代码为main.cpp。

### 5.3 使用流程
创建build文件夹，使用cmake编译src文件后并在build中生成工程文件，使用vs打开文件夹build下面的RuixinSDK_Demo.sln工程文件即可运行示例。

### 5.5 调用流程
Step1：运行demo后，在弹窗主页面，输入"1"可通过调用"updateDeviceInfo()"与"getDeviceInfo()"自动检索设备hostName与IP，若已至设备hostName或IP，可跳过此步骤。
Step2：在弹窗主页面，输入"2"，连接设备，调用connect(hostname)对于手动连接，须设置设备的hostname；对于自动连接，执行"步骤1"自动扫描局域网内可连接设备，并连接找到的第一个设备。
Step3：在弹窗主页面，输入"3"，开始跟踪，调用startTracking()；实时获取当前设备连接状态，调用getConnectionStatus()；刷新实时数据，调用trackingUpdate()；获取实时跟踪数据，调用getTrackingData()。
Step4：在弹窗主页面，输入"4"，停止跟踪，调用stopTracking()。
Step5：在弹窗主页面，输入"5"，断开连接，调用disConnect()。

## 6. 常见问题

### Q1：手动连接设备成功，但自动连接设备失败。
A1：请关闭所有防火墙后，重新自动连接。

### Q2：输入hostName连接设备，出现延迟或卡段问题。
A2：请输入IP连接设备，部分电脑网卡存在刷新慢等问题。
