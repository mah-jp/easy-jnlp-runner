# 🚀 Easy JNLP Runner

Java Web Start (`.jnlp`) ファイルを、モダンな Linux / macOS / Windows 環境で起動するためのPythonスクリプトです。Java Web Start (`javaws`) が利用できない環境や、古いJavaアプレットの互換性問題を解決するために作成されました。

特に、HPE製KVMスイッチ (Avocent OEM) のリモートコンソールなど、署名のない古いJARを使用するアプリケーションをセキュリティ制限を回避して実行するのに最適です。

## ✨ 特徴

* **自動セットアップ**: `.jnlp`ファイルを解析し、必要なJARファイルとネイティブライブラリを自動的にダウンロード・展開します。
* **マルチOS対応**: Linux / macOS / Windows の各環境に対応。OSを自動判別して適切なネイティブライブラリをロードします。
* **強力な互換性対策**:
    * **Linux**: 最新のUbuntu 24.04 (Wayland) で発生するGUIフリーズを回避する自動設定を搭載。
    * **macOS**: JNLPからMac用のネイティブライブラリ (`.jnilib`等) を適切に抽出してロードします。
    * **Windows**: 標準的な Python + Java 環境で、パス設定の手間なくスムーズに起動します。
* **クリーンな実行**: 作業ファイルは一時ディレクトリで管理され、終了時に自動削除されます。

## 本ツールを使用するメリット

*   **「署名なし」でも無条件で実行可能 (最大の理由)**
    OpenWebStartやJava Web Startは、インターネット経由のアプリとして動作するため厳格なセキュリティ機能が働き、署名のない古いKVMアプリはブロックされがちです。本ツールはJARファイルをローカルにダウンロードした後、**「ユーザーが自分の意思で直接実行するローカルのコマンド」**として`java`を呼び出すため、署名チェックやサンドボックス制限を回避して確実に動作させることができます。

## 📋 動作要件

### 動作確認済みKVMスイッチ

| メーカー | モデル名 | バージョン (App / Boot) | ビルド |
| :--- | :--- | :--- | :--- |
| HPE | 0x2x16 G3 KVM Console Switch | 02.02.00.00 / 03.40.00.00 | 4508 |

### Linux (Ubuntu, Debian等)
* **OS**: Ubuntu 24.04 (Noble) での動作を確認済み。
* **Java**: **Java 8 Runtime (OpenJDK 8) 必須**
    * インストール例: `sudo apt install openjdk-8-jre`

### macOS
* **OS**: macOS Monterey以降 (Intel / Apple Silicon)
    * **Apple Silicon 対応**: ARMネイティブ版のJavaを使用すればネイティブ (arm64) で動作します。ただし、古いKVMコンソールなどでIntel版限定のネイティブライブラリが必要な場合は、x86_64版Javaを **Rosetta 2** 経由で実行する必要があります。
* **Java**: **Java 8 または 11 (OpenJDK)**
    * 動作確認済み: OpenJDK 11 (Eclipse Temurin 11)
    * Homebrewでのインストール例: `brew install --cask temurin` (最新LTS) または `brew install --cask temurin8`

## 🚀 使い方

1. KVMスイッチのWeb UIから`session_launch.jnlp` (または`video.jnlp`等) をダウンロードします。
2. ダウンロードした`.jnlp`ファイルを引数に指定してスクリプトを実行します。

### Linux での起動
```bash
# スマートカード機能を無効化し、UIフリーズ対策 (X11強制+ATK無効化) を適用
python3 easy-jnlp-runner.py --no-smartcard --fix-ui session_launch.jnlp
```

### macOS での起動
```bash
# 基本起動
python3 easy-jnlp-runner.py session_launch.jnlp
```
macOSでは`--fix-ui`オプションは不要です (自動的に無視されます)。

### ⚙️ オプション一覧

| オプション | 説明 |
| :--- | :--- |
| `jnlp_file` | 引数として`.jnlp`ファイルのパスを指定します (デフォルト: `session_launch.jnlp`) 。 |
| `--fix-ui` | **[Linux専用]** UIフリーズ対策を適用します。Wayland環境でX11バックエンドを強制し、`AtkWrapper` (アクセシビリティ) を一時的に無効化してデッドロックを防ぎます。 |
| `--no-smartcard` | **[重要]** スマートカードリーダー用ライブラリ (`avctJPCSC`) を除外します。ドライバ読み込み待ちによるハングアップを回避できます。 |
| `--java <path>` | Java実行ファイルのパスを指定します。指定しない場合、Linuxでは所定のパス、macOSでは`java_home`コマンドから自動検出します。 |
| `--use-opengl` | 描画パイプラインを OpenGL に変更します。描画が乱れる場合に試してください。 |
| `--debug` | デバッグモード。一時ファイルを削除せずに残し、ネイティブライブラリの依存関係 (`ldd`等) をチェックします。 |
| `--diagnose` | 診断モード。起動から15秒後に強制的にスレッドダンプを取得して終了します。 |

## 🛠️ 動作テスト (サンプルJARを利用)

リポジトリに含まれる`sample_jar`を使用して、スクリプトの動作をテストできます。バイナリが含まれていないため、最初にコンパイルが必要です。

### 1. サンプルのビルド (JDKが必要)
```bash
cd sample_jar
./compile.sh  # Linux / macOS
compile.bat   # Windows
# ※ hello.jar と hello.class が生成されます
```

### 2. ローカルサーバーの準備
JNLPファイルは通常、ネットワーク経由でJARファイルをロードします。テスト用に`sample_jar`ディレクトリをHTTPサーバーとして公開します。(付属の`hello.jnlp`は`http://localhost:8000`からファイルをロードするように設定されています)

```bash
# ターミナルA (sample_jar 内で実行)
python3 -m http.server 8000
```

### 3. スクリプトの実行
別のターミナルを開き、リポジトリのルートディレクトリから以下のコマンドを実行します。

```bash
# ターミナルB (ルートディレクトリで実行)
python3 easy-jnlp-runner.py sample_jar/hello.jnlp
```

成功すると、一時ディレクトリに`hello.jar`がダウンロードされ、Javaのダイアログボックス ("hello from easy-jnlp-runner!") が表示されます。

## ❓ トラブルシューティング

### Q. [Linux] 起動直後に画面が出ない、または灰色のまま固まる
**A.** GNOMEデスクトップやWayland環境、またはスマートカードドライバの問題の可能性があります。
`python3 easy-jnlp-runner.py --no-smartcard --fix-ui` を試してください。

### Q. [Linux] スクリプト実行後、他の Java アプリの動作がおかしくなった
**A.** スクリプトは実行中、一時的に `~/.accessibility.properties` を書き換えます。通常は終了時に自動復元されますが、強制終了時などに稀に残る場合があります。ファイルが残っている場合は削除、またはバックアップ (`.bak`) から復元してください。

### Q. [macOS] "java" コマンドが見つからないと言われる
**A.** Java 8 がインストールされていないか、パスが認識されていません。
`brew install --cask temurin8` でインストールするか、`--java /Library/Internet\ Plug-Ins/JavaAppletPlugin.plugin/Contents/Home/bin/java` のように明示的にパスを指定してください。

### Q. "Access Denied" (アクセス拒否)
**A.** JNLPファイルに含まれる認証トークンの有効期限切れです。
KVMのWeb画面から再度「起動」ボタンを押し、新しいJNLPファイルをダウンロードしてすぐに実行してください。

## 📄 ライセンス

[MIT License](LICENSE)

## 👤 作者
Masahiko OHKUBO (https://github.com/mah-jp)
