const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
const scriptMatch = html.match(/<script type="text\/babel">([\s\S]*?)<\/script>/);
if (scriptMatch) {
    fs.writeFileSync('extracted.jsx', scriptMatch[1]);
    console.log("JSX extracted. Line 323:", scriptMatch[1].split('\n')[322]);
}
