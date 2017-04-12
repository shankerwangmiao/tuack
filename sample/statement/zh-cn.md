{{ self.title() }}

## 问题描述

现在子标题都不加方括号 `【】` 了。

**要强调的东西**这么写。

行内的公式：$sin \left(a x + b \right)$。

行间的公式：
$$
\frac{-b\pm\sqrt{b^2-4ac}}{2a}
$$

1. 第一点
2. 第二点

* 第一点
* 第二点

字符串或代码 `This is a string`

```
int main(int argc, char** argv);
```

不要用markdown自带的语法插入图片（因为目前支持不好），用下列语法插入图片：

{{ render("template('image', resource = resource('3.jpg'), size = 0.5, align = 'middle', inline = False)") }}

其中 `inline` 为 `False` 表示这是一个独占一行的图片，此时支持 `align`，选项为 `left`，`middle` 或 `right`。

图片需要保存在试题目录的 `resources` 子目录下。

如果有本工具不能提供的功能，需要直接使用 tex 或 html 代码的，请使用下列方式以免另外一种格式下出错。

{{ render("'\\clearpage'", 'noi') }}

{{ render(''' '<a href="http://oj.thusaac.org">TUOJ</a>' ''', 'html') }}

上述第一个例子是为了排版好看强行加入一个分页符的意思，其中 `noi` 表示只在生成 NOI 风格题面的时候使用这个；第二个例子是在生成任何 html 格式题目的时候加入一个广告（雾）。

可选的参数有 `html`，`tex`，`noi`，`uoj`，`ccpc`，`ccc`，`tuoj`，`ccc-tex`，`ccc-html`，`tuoj-tex`，`tuoj-html`。

## 输入格式

{{ self.input_file() }}

上面会根据具体的评测环境说明输入是文件还是标准输入等。

输入第一行包含一个正整数 $n$，保证 $n \le {{ tools.hn(prob.args['n']) }}$。←这是引用 `conf.json` 中的 `args` 的 `n` 项，然后用“好看”的格式输出。引用时既可以 `['args']` 也可以 `.args`；“好看”的格式如 `$10^9$`，`1,000,000,007`。

## 输出格式

{{ self.output_file() }}

下面是自动读入样例 `1.in/ans` 然后渲染到题面中；如果只有一组样例，则去掉前两行，样例仍然保存成 `1.in/ans`。其中 `1` 可以是字符串。

{% set vars = {} -%}
{%- do vars.__setitem__('sample_id', 1) -%}
{{ self.sample_text() }}

下面是只提示存在第二组样例，但不渲染到题面中。

{% do vars.__setitem__('sample_id', 2) -%}
{{ self.sample_file() }}

## 子任务

同样不建议用markdown原生的表格，使用下列方式渲染一个表格，其中表格存放在试题目录的 `tables` 子目录下。

{{ render("table('data')") }}

{{ render("table('table', {'width' : [1, 6]})") }}

表格的例子见 `oi_tools/sample/tables`。原理上用一个二维的json表格存储，`null` 表示和上一行合并，不支持横向合并。建议用jinja的格式写，如例子中的 `data.json`，这样可以根据数据生成；跟数据无关的表格则可以像 `table.json` 那样存储。