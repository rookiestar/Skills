#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");

const SKILL_NAME = "self-learning-tutor";
const PACKAGE_ROOT = path.resolve(__dirname, "..");
const WORKSPACE_SKILLS_DIR = path.join(os.homedir(), ".openclaw", "workspace", "skills");
const LEGACY_OPENCLAW_TARGET = path.join(os.homedir(), ".openclaw", "skills", SKILL_NAME);
const WORKSPACE_TARGET = path.join(WORKSPACE_SKILLS_DIR, SKILL_NAME);

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
  const items = ["SKILL.md", "references", "scripts", "data", "package.json"];
  for (const legacyTarget of [LEGACY_OPENCLAW_TARGET]) {
    if (fs.existsSync(legacyTarget)) {
      fs.rmSync(legacyTarget, { recursive: true, force: true });
    }
  }
  if (fs.existsSync(WORKSPACE_TARGET)) {
    fs.rmSync(WORKSPACE_TARGET, { recursive: true, force: true });
  }
  fs.mkdirSync(WORKSPACE_TARGET, { recursive: true });
  for (const item of items) {
    const source = path.join(PACKAGE_ROOT, item);
    if (fs.existsSync(source)) {
      copyRecursive(source, path.join(WORKSPACE_TARGET, item));
    }
  }

  console.log(`Installed ${SKILL_NAME} to:`);
  console.log(`  - ${WORKSPACE_TARGET}`);
}

function uninstall() {
  let removed = false;
  for (const targetDir of [LEGACY_OPENCLAW_TARGET, WORKSPACE_TARGET]) {
    if (!fs.existsSync(targetDir)) {
      continue;
    }
    fs.rmSync(targetDir, { recursive: true, force: true });
    removed = true;
  }
  console.log(removed ? `Removed ${SKILL_NAME} from all known install locations.` : `${SKILL_NAME} is not installed.`);
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
