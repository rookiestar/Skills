#!/usr/bin/env node

/**
 * eng-lang-tutor CLI
 *
 * Commands:
 *   install   - Install the skill to ~/.openclaw/skills/eng-lang-tutor/
 *   uninstall - Remove the skill from ~/.openclaw/skills/eng-lang-tutor/
 */

const path = require('path');
const fs = require('fs');
const os = require('os');

const SKILL_NAME = 'eng-lang-tutor';
const SKILLS_DIR = path.join(os.homedir(), '.openclaw', 'skills');
const SKILL_TARGET = path.join(SKILLS_DIR, SKILL_NAME);

// Get the package root directory (where package.json is)
const PACKAGE_ROOT = path.resolve(__dirname, '..');

function getSkillSourceDir() {
  return PACKAGE_ROOT;
}

function install() {
  console.log(`Installing ${SKILL_NAME} skill...`);

  const sourceDir = getSkillSourceDir();

  // Check if source directory exists
  if (!fs.existsSync(sourceDir)) {
    console.error(`Error: Source directory not found: ${sourceDir}`);
    process.exit(1);
  }

  // Create skills directory if it doesn't exist
  if (!fs.existsSync(SKILLS_DIR)) {
    fs.mkdirSync(SKILLS_DIR, { recursive: true });
    console.log(`Created skills directory: ${SKILLS_DIR}`);
  }

  // Remove existing installation if present
  if (fs.existsSync(SKILL_TARGET)) {
    console.log(`Removing existing installation at ${SKILL_TARGET}...`);
    fs.rmSync(SKILL_TARGET, { recursive: true, force: true });
  }

  // Create target directory
  fs.mkdirSync(SKILL_TARGET, { recursive: true });

  // Files and directories to copy
  const itemsToCopy = [
    'scripts',
    'templates',
    'references',
    'examples',
    'docs',
    'SKILL.md',
    'CLAUDE.md',
    'README.md',
    'README_EN.md',
    'requirements.txt'
  ];

  // Copy each item
  for (const item of itemsToCopy) {
    const sourcePath = path.join(sourceDir, item);
    const targetPath = path.join(SKILL_TARGET, item);

    if (!fs.existsSync(sourcePath)) {
      console.log(`  Skipping ${item} (not found)`);
      continue;
    }

    try {
      if (fs.statSync(sourcePath).isDirectory()) {
        copyDir(sourcePath, targetPath);
      } else {
        fs.copyFileSync(sourcePath, targetPath);
      }
      console.log(`  Copied ${item}`);
    } catch (err) {
      console.error(`  Error copying ${item}: ${err.message}`);
    }
  }

  console.log(`\n✓ ${SKILL_NAME} installed to ${SKILL_TARGET}`);
  console.log('\nNext steps:');
  console.log('  1. Install Python dependencies:');
  console.log(`     pip install -r ${SKILL_TARGET}/requirements.txt`);
  console.log('  2. Restart your OpenClaw agent');
  console.log('  3. Configure the skill through the onboarding flow');
}

function uninstall() {
  console.log(`Uninstalling ${SKILL_NAME} skill...`);

  if (!fs.existsSync(SKILL_TARGET)) {
    console.log(`${SKILL_NAME} is not installed.`);
    return;
  }

  try {
    fs.rmSync(SKILL_TARGET, { recursive: true, force: true });
    console.log(`✓ ${SKILL_NAME} removed from ${SKILL_TARGET}`);
    console.log('\nNote: Your learning data is preserved at:');
    console.log('  ~/.openclaw/state/eng-lang-tutor/');
    console.log('\nTo completely remove all data, run:');
    console.log('  rm -rf ~/.openclaw/state/eng-lang-tutor');
  } catch (err) {
    console.error(`Error uninstalling: ${err.message}`);
    process.exit(1);
  }
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });

  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function showHelp() {
  console.log(`
eng-lang-tutor - English Language Tutor Skill for OpenClaw

Usage:
  eng-lang-tutor <command>

Commands:
  install     Install the skill to ~/.openclaw/skills/eng-lang-tutor/
  uninstall   Remove the skill (preserves learning data)
  help        Show this help message

Environment Variables:
  OPENCLAW_STATE_DIR  Custom directory for learning data
                      (default: ~/.openclaw/state/eng-lang-tutor)

Examples:
  eng-lang-tutor install
  eng-lang-tutor uninstall
`);
}

// Main
const command = process.argv[2];

switch (command) {
  case 'install':
    install();
    break;
  case 'uninstall':
    uninstall();
    break;
  case 'help':
  case '--help':
  case '-h':
    showHelp();
    break;
  default:
    if (command) {
      console.error(`Unknown command: ${command}`);
    }
    showHelp();
    process.exit(command ? 1 : 0);
}
