#!/usr/bin/env node

/**
 * Post-install script for @rookiestar/eng-lang-tutor
 *
 * This script runs automatically after npm install and:
 * 1. Installs the skill to ~/.openclaw/skills/eng-lang-tutor/
 * 2. Migrates data from old data/ directory if needed (handled by Python code)
 */

const path = require('path');
const fs = require('fs');
const os = require('os');

const SKILL_NAME = 'eng-lang-tutor';
const SKILLS_DIR = path.join(os.homedir(), '.openclaw', 'skills');
const SKILL_TARGET = path.join(SKILLS_DIR, SKILL_NAME);

// Get the package root directory
const PACKAGE_ROOT = path.resolve(__dirname, '..');

function install() {
  console.log(`\n📦 Setting up ${SKILL_NAME} skill...\n`);

  // Create skills directory if it doesn't exist
  if (!fs.existsSync(SKILLS_DIR)) {
    fs.mkdirSync(SKILLS_DIR, { recursive: true });
    console.log(`✓ Created skills directory: ${SKILLS_DIR}`);
  }

  // Remove existing installation if present
  if (fs.existsSync(SKILL_TARGET)) {
    console.log(`✓ Updating existing installation...`);
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
  let copiedCount = 0;
  for (const item of itemsToCopy) {
    const sourcePath = path.join(PACKAGE_ROOT, item);
    const targetPath = path.join(SKILL_TARGET, item);

    if (!fs.existsSync(sourcePath)) {
      continue;
    }

    try {
      if (fs.statSync(sourcePath).isDirectory()) {
        copyDir(sourcePath, targetPath);
      } else {
        fs.copyFileSync(sourcePath, targetPath);
      }
      copiedCount++;
    } catch (err) {
      console.error(`  Warning: Could not copy ${item}: ${err.message}`);
    }
  }

  console.log(`✓ Copied ${copiedCount} items to ${SKILL_TARGET}`);

  // Show post-install message
  console.log(`
╔═══════════════════════════════════════════════════════════════╗
║                   Installation Complete!                      ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ${SKILL_NAME} has been installed to:                          ║
║  ${SKILL_TARGET}
║                                                               ║
║  Next steps:                                                  ║
║  1. Install Python dependencies:                              ║
║     pip install -r ${SKILL_TARGET}/requirements.txt           ║
║                                                               ║
║  2. Restart your OpenClaw agent                               ║
║                                                               ║
║  3. Configure through onboarding (first time only)            ║
║                                                               ║
║  Data location:                                               ║
║     ~/.openclaw/state/eng-lang-tutor/                         ║
║     (or set OPENCLAW_STATE_DIR env var)                       ║
║                                                               ║
║  Commands:                                                    ║
║     npx eng-lang-tutor install    - Reinstall skill           ║
║     npx eng-lang-tutor uninstall  - Remove skill              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
`);
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

// Run installation
try {
  install();
} catch (err) {
  console.error(`\n❌ Installation failed: ${err.message}`);
  console.error('You may need to run the install manually:');
  console.error('  npx eng-lang-tutor install\n');
  process.exit(0); // Don't fail npm install
}
