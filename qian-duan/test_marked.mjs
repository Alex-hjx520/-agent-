// 临时测试：marked 是否解析表格（测后删除）
import { marked } from 'marked'

const md = `# 设备选型报告

## 1. 用户需求

| 需求项 | 要求 |
| :--- | :--- |
| 设备类型 | 电磁阀 (KDF 系列) |
| 系统环境 | 干式系统 |

## 2. 最终选型

- 型号：KDF6H
`

console.log('=== marked.parse 输出 ===')
const html = marked.parse(md)
console.log(html)
console.log('=== 是否含 <table>:', html.includes('<table'))
console.log('=== 是否含管道符 |:', html.includes('|'))
console.log('=== marked 默认 gfm:', marked.defaults.gfm)
