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
- 无法独自完成设备之间的认证和授权（依赖GNOME）工作
- 主程序不支持配置选项
- 不支持systemd集成

我希望通过开源，可以将对此项目感兴趣的朋友聚集到一起，让此方案的功能不断完善。

体验方法
========

系统要求如下：

- 蓝牙硬件
- BlueZ(>=5)
- python(>=2.7)
- [evdev](https://pypi.python.org/pypi/evdev)
- [dbus-python](https://pypi.python.org/pypi/dbus-python)
- [PyBlueZ](https://pypi.python.org/pypi/PyBluez)
- iOS或者Android设备

系统准备好之后需要对源代码做少许修改。我的电脑的键盘设备节点是`/dev/input/event3`，所以我就将路径硬编码到程序中了。大家需要找到自己的键盘设备节点，然后对btk.py中的第13行做相应更改。

```py
keyboard = kb.Keyboard('/dev/input/event3')
```

启动蓝牙之后以root用户运行btk.py脚本就可以了。
