#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");

const SKILL_NAME = "self-learning-tutor";
const PACKAGE_ROOT = path.resolve(__dirname, "..");
const SKILLS_DIR = path.join(os.homedir(), ".openclaw", "skills");
const TARGET_DIR = path.join(SKILLS_DIR, SKILL_NAME);

function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src)) {
      copyRecursive(path.join(src, entry), path.join(dest, entry));
    }
    return;
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
}

function install() {
  fs.mkdirSync(SKILLS_DIR, { recursive: true });
  if (fs.existsSync(TARGET_DIR)) {
    fs.rmSync(TARGET_DIR, { recursive: true, force: true });
  }
  fs.mkdirSync(TARGET_DIR, { recursive: true });

  const items = ["SKILL.md", "references", "scripts", "data", "package.json"];
  for (const item of items) {
    const source = path.join(PACKAGE_ROOT, item);
    if (fs.existsSync(source)) {
      copyRecursive(source, path.join(TARGET_DIR, item));
    }
  }

  console.log(`Installed ${SKILL_NAME} to ${TARGET_DIR}`);
}

function uninstall() {
  if (!fs.existsSync(TARGET_DIR)) {
    console.log(`${SKILL_NAME} is not installed.`);
    return;
  }
  fs.rmSync(TARGET_DIR, { recursive: true, force: true });
  console.log(`Removed ${TARGET_DIR}`);
}

function help() {
  console.log(`
self-learning-tutor

Usage:
  self-learning-tutor install
  self-learning-tutor uninstall
  self-learning-tutor help
`);
}

const command = process.argv[2];

switch (command) {
  case "install":
    install();
    break;
  case "uninstall":
    uninstall();
    break;
  case "help":
  case "--help":
  case "-h":
  case undefined:
    help();
    break;
  default:
    console.error(`Unknown command: ${command}`);
    help();
    process.exit(1);
}
