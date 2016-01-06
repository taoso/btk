btk
---
蓝牙虚拟键盘

缘起
====
我本人是键盘党，喜欢快捷键。我又是程序员，需要疯狂地敲代码。我还是iPad的粉丝，一边敲代码，一边用iPad看文档。问题来了，看文档的时候手因为要操作iPad而不得不离开键盘，这让我感到绝望。所以我就一直在想，能不能使用PC的键盘控制iPad呢？答案是肯定的，因为我已经实现了。并非所有能达到目的的方案都可以，我认为合理的方案应该满足以下需求：

1. iPad无需越狱
2. iPad无需安装程序
3. 支持Arch Linux

我没有苹果开发者帐号，也不会开发iOS程序，所以规定了第二条。另一方面，第二条也提高了系统易用性。

我是Arch Linux的粉丝。Arch滚动发布，升级比较快，系统的各个软件版本都很新。所以合理的方案应该兼容最新的系统。

想来想去，也就只有蓝牙键盘能够满足以上要求了。也就是说，我们使用蓝牙协议将电脑虚拟成一个蓝牙HID输入设备。这样iPad就会自动识别我们的电脑了。

要想实现一个蓝牙键盘，需要做以下工作：

- 学习蓝牙HIDP协议栈
- 学习Linux系统下的蓝牙编程技术

HIDP协议栈全文可以从蓝牙官网下载到，但是是英文的，啃吧。而Linux下的蓝牙协议栈是BlueZ，最新的版本则是5.x。BlueZ对外提供DBus接口，所以还得研究以下DBus编程规范。

另一方面，我们从来都不是一个人在战斗。前人在相关领域已经有了丰富的研究成果。本项目主要参考了两个项目，一个是[btkbdd](http://v3.sk/~lkundrak/btkbdd/)，另一个则是[PiTooth](http://www.linuxuser.co.uk/tutorials/emulate-a-bluetooth-keyboard-with-the-raspberry-pi)。我借鉴了PiTooth读取系统键盘事件的实现（evdev），直接借用了PiTooth的sdp定义文件和键盘映射文件。而btkbdd项目则提供关于iPad相关的珍贵细节问题，为我节省了不少时间。当然了，这两个项目都比较古老，无法适应Arch Linux系统，其中的根本原因是BlueZ进入5.x版本后放弃了前向兼容。我使用Python，充分利用BlueZ的新接口，提供了蓝牙键盘的一种简单实现。

到目前为止，btk可以与iPad和安卓手机正常配合工作，但仍然有一些问题：

- 无法支持多设备连接
- 无法很优雅地处理设备断掉连接的情况
- 主程序不支持配置选项
- 不支持systemd集成

我希望通过开源，可以将对此项目感兴趣的朋友聚集到一起，让此方案的功能不断完善。

体验方法
========

系统要求如下：

- 蓝牙硬件
- BlueZ(>=5)
- python(>=2.7)
- [PyGObject](https://live.gnome.org/PyGObject)
- [evdev](https://pypi.python.org/pypi/evdev)
- [pydbus]()
- [PyBlueZ](https://pypi.python.org/pypi/PyBluez)
- iOS或者Android设备

首先，运行脚本：
```bash
sudo python agent.py
```

然后使用手机搜索蓝牙，找到你的主机点击配对。这时agent.py脚本会提示你输入配对码。直接输入并回车即可开启体验之旅。

键鼠HID报告描述符
=================
以下是一个具有键盘和鼠标功能的HID描述符，具体参见USB HID协议。
```
0x05, 0x01, // UsagePage GenericDesktop
0x09, 0x02, // Usage Mouse
0xA1, 0x01, // Collection Application
0x85, 0x01, // REPORT ID: 1
0x09, 0x01, // Usage Pointer
0xA1, 0x00, // Collection Physical
0x05, 0x09, // UsagePage Buttons
0x19, 0x01, // UsageMinimum 1
0x29, 0x03, // UsageMaximum 3
0x15, 0x00, // LogicalMinimum 0
0x25, 0x01, // LogicalMaximum 1
0x75, 0x01, // ReportSize 1
0x95, 0x03, // ReportCount 3
0x81, 0x02, // Input data variable absolute
0x75, 0x05, // ReportSize 5
0x95, 0x01, // ReportCount 1
0x81, 0x01, // InputConstant (padding)
0x05, 0x01, // UsagePage GenericDesktop
0x09, 0x30, // Usage X
0x09, 0x31, // Usage Y
0x09, 0x38, // Usage ScrollWheel
0x15, 0x81, // LogicalMinimum -127
0x25, 0x7F, // LogicalMaximum +127
0x75, 0x08, // ReportSize 8
0x95, 0x02, // ReportCount 3
0x81, 0x06, // Input data variable relative
0xC0, 0xC0, // EndCollection EndCollection
0x05, 0x01, // UsagePage GenericDesktop
0x09, 0x06, // Usage Keyboard
0xA1, 0x01, // Collection Application
0x85, 0x02, // REPORT ID: 2
0xA1, 0x00, // Collection Physical
0x05, 0x07, // UsagePage Keyboard
0x19, 0xE0, // UsageMinimum 224
0x29, 0xE7, // UsageMaximum 231
0x15, 0x00, // LogicalMinimum 0
0x25, 0x01, // LogicalMaximum 1
0x75, 0x01, // ReportSize 1
0x95, 0x08, // ReportCount 8
0x81, 0x02, // **Input data variable absolute
0x95, 0x08, // ReportCount 8
0x75, 0x08, // ReportSize 8
0x15, 0x00, // LogicalMinimum 0
0x25, 0x65, // LogicalMaximum 101
0x05, 0x07, // UsagePage Keycodes
0x19, 0x00, // UsageMinimum 0
0x29, 0x65, // UsageMaximum 101
0x81, 0x00, // **Input DataArray
0xC0, 0xC0, // EndCollection
```
摘自[Python编程.Bluetooth HID Mouse and Keyboard（一）](http://blog.csdn.net/huipengzhao/article/details/18268201)。

将以上描述符去掉`0x`、`,`和注释，拼成一行放入HID描述xml文件的`HID Descriptor`属性即可。
