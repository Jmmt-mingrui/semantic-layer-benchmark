# OKF 原生消费者

[English](README.md) | [简体中文](README.zh-CN.md)

`OkfNativeConsumer` 以 OKF 的原生形式评测知识包：原始 Markdown、YAML
frontmatter、索引和本地链接。它不是语义查询引擎，不执行查询，也不会把
知识包转换成共享检索表示。

## 边界

消费者仅暴露注册表声明的 OKF 操作：

- `okf.validate_frontmatter`
- `okf.validate_links`
- `okf.list_files`
- `okf.read_file`
- `okf.follow_link`
- `okf.search_text`

`search_text` 是对源 Markdown 的显式字面扫描，从不构建 embedding 索引。
消费者不依赖数据库，也不提供 SQL fallback。每次读文件都会返回 SHA-256；
访问遥测仅记录净化后的操作元数据、工件身份、耗时和结果数量。

## 隔离规则

- 启动前校验 artifact root；evaluator-only 和 Gold 根目录会被拒绝。
- 所有路径必须相对于知识包根目录、仅限 Markdown，且解析后仍位于声明根
  目录内。绝对路径、`..`、符号链接及符号链接逃逸都会 fail closed。
- 只有源文档实际声明的本地链接才可以被跟随。
- 构造对象时不会扫描知识包。文件只会在显式操作时读取，因此 agent 没有
  preload-all 上下文。

该 adapter 只是协议组件：它不生成分数、run record 或正式结果，必须与独立的
evaluator-only 组件配合使用。
