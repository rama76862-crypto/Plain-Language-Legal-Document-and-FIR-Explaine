/**
 * Check i18n key parity between en, hi, pa dictionaries.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import ts from 'typescript';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function extractKeys(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  // Simple regex parser to extract top-level and second-level keys
  const keys = new Set();
  const lines = content.split('\n');
  let currentGroup = '';

  for (const line of lines) {
    const groupMatch = line.match(/^\s{2}([a-zA-Z0-9_]+):\s*\{/);
    if (groupMatch) {
      currentGroup = groupMatch[1];
      continue;
    }
    const keyMatch = line.match(/^\s{4}([a-zA-Z0-9_]+):/);
    if (keyMatch && currentGroup) {
      keys.add(`${currentGroup}.${keyMatch[1]}`);
    }
  }
  return keys;
}

const localesDir = path.resolve(__dirname, '../src/locales');
const enKeys = extractKeys(path.join(localesDir, 'en.ts'));
const hiKeys = extractKeys(path.join(localesDir, 'hi.ts'));
const paKeys = extractKeys(path.join(localesDir, 'pa.ts'));

console.log(`Checking i18n dictionaries:`);
console.log(`- en.ts keys: ${enKeys.size}`);
console.log(`- hi.ts keys: ${hiKeys.size}`);
console.log(`- pa.ts keys: ${paKeys.size}`);

let hasMismatch = false;

// Check missing in hi
for (const key of enKeys) {
  if (!hiKeys.has(key)) {
    console.error(`Missing in hi.ts: ${key}`);
    hasMismatch = true;
  }
  if (!paKeys.has(key)) {
    console.error(`Missing in pa.ts: ${key}`);
    hasMismatch = true;
  }
}

function checkUsages(directory) {
  for(const entry of fs.readdirSync(directory,{withFileTypes:true})) {
    const filename=path.join(directory,entry.name);
    if(entry.isDirectory()) {checkUsages(filename);continue;}
    if(!/\.tsx?$/.test(filename)) continue;
    const source=ts.createSourceFile(filename,fs.readFileSync(filename,'utf8'),ts.ScriptTarget.Latest,true,filename.endsWith('.tsx')?ts.ScriptKind.TSX:ts.ScriptKind.TS);
    function visit(node) {
      if(ts.isCallExpression(node)&&ts.isIdentifier(node.expression)&&node.expression.text==='t'&&node.arguments.length&&ts.isStringLiteral(node.arguments[0])&&!enKeys.has(node.arguments[0].text)) {
        console.error(`Missing dictionary key used in ${path.relative(localesDir,filename)}: ${node.arguments[0].text}`);
        hasMismatch=true;
      }
      ts.forEachChild(node,visit);
    }
    visit(source);
  }
}
checkUsages(path.resolve(__dirname,'../src'));

if (!hasMismatch) {
  console.log('✅ All keys in en.ts are mirrored in hi.ts and pa.ts with 100% parity!');
  process.exit(0);
} else {
  console.error('❌ Mismatches found!');
  process.exit(1);
}
