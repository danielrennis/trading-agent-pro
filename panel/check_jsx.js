const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
const scriptMatch = html.match(/<script type="text\/babel">([\s\S]*?)<\/script>/);
const code = scriptMatch[1];
const { parse } = require('@babel/parser');

try {
  parse(code, { plugins: ['jsx'] });
  console.log("No syntax error!");
} catch (e) {
  console.error(e.message);
}
