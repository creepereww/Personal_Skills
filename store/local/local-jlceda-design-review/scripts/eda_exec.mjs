import fs from 'node:fs';

const file = process.argv[2];
const port = process.argv[3] || '49620';
if (!file) {
  console.error('usage: node eda_exec.mjs <js-file> [port]');
  process.exit(2);
}
const code = fs.readFileSync(file, 'utf8');
const res = await fetch(`http://127.0.0.1:${port}/execute`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ code }),
});
const text = await res.text();
try {
  const json = JSON.parse(text);
  if (json.success === false) {
    console.log('ERROR:', json.error ?? text);
    process.exit(1);
  }
  console.log(typeof json.result === 'string' ? json.result : JSON.stringify(json.result, null, 2));
} catch {
  console.log(text);
}
