# appharbor-repacked

把 [BeiChen-CN/AppHarbor](https://github.com/BeiChen-CN/AppHarbor) 重新打包成 **`com.xiaomi.market`**
（HyperOS 的 MIUISuperMarket）身份。每天检查上游 release，有新版本就自动重打包、签名、发 Release。

仓库只负责产出可装的 APK，**不碰你的设备**：没有 adb 自动化、没有定时安装、不需要 token。

## 产物

<https://github.com/FairyJJ/appharbor-repacked/releases>

```
appharbor-<upstream-tag>-repacked.apk
SHA256SUMS.txt
```

取用：

```sh
./scripts/download-latest.sh              # 下到 ./dist
adb install -r -t ./dist/appharbor-*-repacked.apk
```

## 替换映射

| | |
|---|---|
| 上游 | `BeiChen-CN/AppHarbor`（含 prerelease） |
| 原始包名 | `com.app.market` |
| 目标包名 | `com.xiaomi.market` |
| versionCode | 钉死 **99999999** |
| 类目录 | **搬**（`--move-classes`） |
| Compose 资源 | **改名**（`--rename-assets`） |

## 为什么 versionCode 钉死 99999999

`PackageManagerService` 开机扫描系统包时，若 `/data/app` 里该包 versionCode **小于**系统分区上的版本，
判定为「系统应用已升级、data 版是旧残留」，直接删掉 data 版 → 退回原版。

所以「不装模块、纯覆盖安装」要长期有效，data 版 versionCode 必须 **大于** 系统原版。

代价：应用内「检查更新」永远认为已是最新，升级只能从本仓库 Release 手动拉包覆盖安装。

## 工作流

`.github/workflows/build.yml`

- 触发：每天 03:00 UTC（11:00 CST）+ 手动 `workflow_dispatch`（勾 `force` 可强制重建）
- 解析上游最新 release（**包含 prerelease**）
- 若 `appharbor-<tag>` 这个 Release 已存在 → 跳过，不浪费构建时间
- 否则下载 APK → `scripts/repack.py` → 发布 Release + 上传 artifact

## 坑（脚本里已处理）

1. **apktool 的 build 缓存**：改完 `apktool.yml` 的 `versionInfo.versionCode` 直接 `b`，
   apktool 打印 `AndroidManifest.xml and resources have not changed` 且**不写入**新 versionCode。
   必须先 `rm -rf src/build`，脚本会强制清理并在构建后校验。
2. **Compose Multiplatform 资源路径**：`assets/composeResources/<pkg>.resources` 是按包名生成的目录，
   只改 smali 字符串不改目录名 → 启动即 `Missing resource with path` 崩溃。这里必须 `--rename-assets`。
3. **类目录要跟着搬**：`smali/com/app/market` → `smali/com/xiaomi/market`，否则 `ClassNotFoundException`。
4. **签名固定**：uber-apk-signer 内置 debug key，每次构建签名一致，覆盖安装不冲突。

## 手动构建（本地）

```sh
curl -fsSL -o apktool.jar https://github.com/iBotPeaches/Apktool/releases/download/v3.0.3/apktool_3.0.3.jar
curl -fsSL -o uber-apk-signer.jar https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar

APKTOOL_JAR=./apktool.jar SIGNER_JAR=./uber-apk-signer.jar \
python3 scripts/repack.py \
  --apk AppHarbor.apk \
  --old com.app.market \
  --new com.xiaomi.market \
  --version-code 99999999 \
  --move-classes --rename-assets \
  --out-dir dist
```

## 回退

```sh
adb shell "pm uninstall-system-updates com.xiaomi.market"
```

## 上游与致谢

| | |
|---|---|
| 上游项目 | [BeiChen-CN/AppHarbor](https://github.com/BeiChen-CN/AppHarbor) |
| 上游作者 | [@BeiChen-CN](https://github.com/BeiChen-CN) |
| 上游前身 | [YXBwbWFya2V0/AppMarket](https://github.com/YXBwbWFya2V0/AppMarket)（KMP 跨平台应用商店） |
| 上游许可证 | **未声明**（上游仓库及其 fork 源均无 LICENSE 文件） |
| 本仓库性质 | 非官方，仅做包名替换 + 重签名 |

AppHarbor 的全部功能、界面、业务逻辑均为上游作者的成果。本仓库**不修改任何业务代码**，
只把 `applicationId` 从 `com.app.market` 换成 `com.xiaomi.market`、抬 versionCode，
以便顶替 HyperOS 自带的 MIUISuperMarket。原项目请见上方链接，建议优先支持上游。

⚠️ **授权提示**：上游未提供开源许可证，按默认版权保留（All rights reserved）处理。
本仓库产物仅供个人在自有设备上做系统应用替换实验，**不构成再分发授权**。
如需向他人分发，请先联系上游作者取得许可。

## 许可证

- `scripts/`、`.github/` 下的构建脚本由本仓库维护者编写，可自由使用与修改。
- APK 产物是上游作品的派生：版权与许可归 **BeiChen-CN / YXBwbWFya2V0** 所有，适用其原始条款。

