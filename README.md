# _BackSoundRec_

由于本人有思念过往的疾病, 故制作此工具安装在班级电脑上

Pyinstaller 打包版本在`dist\BackSoundRec`下

记得给工具设置管理员权限
开机自启可能无法自动设置, 自己整个快捷方式放到`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`吧
运行工具后先设置好同目录下的`config.json`, 再到任务管理器结束程序再启动程序从而读取新配置

默认数据目录: `D:\BSR-Data`
默认音频格式: `AAC`
默认码率: `400k`
默认录音间隔: `15min`
