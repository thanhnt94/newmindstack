import bbcode
parser = bbcode.Parser()
# Built-in color formatter is usually registered by default or we need to check how it behaves 
# if we just use default Parser().
# Let's inspect default formatters.
print(f"Formatters: {list(parser.formatters.keys())}")

text1 = '[color=red]Text 1[/color]'
text2 = '[color="red"]Text 2[/color]'
text3 = '[color=&quot;red&quot;]Text 3[/color]' # in case of html escape before parsing

print(f"Result 1: {parser.format(text1)}")
print(f"Result 2: {parser.format(text2)}")
