# hls 流下载器

要用此下载器必须要有 python3.7+ 环境

## 安装依赖

`pip install -r requirements.txt`

## 运行

> 用来下载网络小说,目前只支持笔趣阁

`python app.py {下载后的文件名} {目录地址} [-p] 下载并发数`

查看帮助
`python app.py -h`

- [x] 支持退出后可继续下载(可以随时 `ctrl + c` 退出,然后再次运行继续下载,name 不变即可)
- [x] 支持代理 
