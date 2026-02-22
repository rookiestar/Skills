#!/usr/bin/env node

/**
 * Post-install script for @rookiestar/eng-lang-tutor
 *
 * This script runs automatically after npm install and:
 * 1. Installs the skill to ~/.openclaw/skills/eng-lang-tutor/
 * 2. Creates Python venv and installs dependencies
 * 3. Checks for system dependencies (ffmpeg)
 * 4. Migrates data from old data/ directory if needed (handled by Python code)
 */

const path = require('path');
const fs = require('fs');
const os = require('os');
const { execSync, spawn } = require('child_process');

const SKILL_NAME = 'eng-lang-tutor';
const SKILLS_DIR = path.join(os.homedir(), '.openclaw', 'skills');
const SKILL_TARGET = path.join(SKILLS_DIR, SKILL_NAME);
const VENV_DIR = path.join(os.homedir(), '.venvs', SKILL_NAME);

// Get the package root directory
const PACKAGE_ROOT = path.resolve(__dirname, '..');

function checkFfmpeg() {
  try {
    execSync('ffmpeg -version', { stdio: 'ignore' });
    return true;
  } catch (e) {
    return false;
  }
}

function setupPythonVenv() {
  const requirementsPath = path.join(SKILL_TARGET, 'requirements.txt');

  // Check if requirements.txt exists
  if (!fs.existsSync(requirementsPath)) {
    console.log('⚠️  requirements.txt not found, skipping Python setup\n');
    return false;
  }

  // Check if venv already exists and has dependencies
  const venvPython = path.join(VENV_DIR, 'bin', 'python');
  const venvPip = path.join(VENV_DIR, 'bin', 'pip');

  if (fs.existsSync(venvPython) && fs.existsSync(venvPip)) {
    // Check if websocket-client is installed (key dependency)
    try {
      execSync(`${venvPython} -c "import websocket"`, { stdio: 'ignore' });
      console.log('✓ Python venv already set up with dependencies\n');
      return true;
    } catch (e) {
      console.log('→ Updating Python dependencies...');
    }
  } else {
    console.log('→ Creating Python virtual environment...');
    try {
      execSync(`python3 -m venv ${VENV_DIR}`, { stdio: 'inherit' });
      console.log('✓ Created venv at ' + VENV_DIR);
    } catch (e) {
      console.log('⚠️  Failed to create venv: ' + e.message);
      return false;
    }
  }

  // Install dependencies
  console.log('→ Installing Python dependencies...');
  try {
    execSync(`${venvPip} install -q -r ${requirementsPath}`, { stdio: 'inherit' });
    console.log('✓ Python dependencies installed\n');
    return true;
  } catch (e) {
    console.log('⚠️  Failed to install Python dependencies: ' + e.message);
    console.log('   You may need to run manually:');
    console.log(`   ${venvPip} install -r ${requirementsPath}\n`);
    return false;
  }
}

function install() {
  console.log(`\n📦 Setting up ${SKILL_NAME} skill...\n`);

  // Check for ffmpeg
  const hasFfmpeg = checkFfmpeg();
  if (!hasFfmpeg) {
    console.log('⚠️  WARNING: ffmpeg is not installed. Audio generation will not work.');
    console.log('   Install it with:');
    if (process.platform === 'darwin') {
      console.log('     brew install ffmpeg');
    } else if (process.platform === 'linux') {
      console.log('     sudo apt-get install ffmpeg   # Debian/Ubuntu');
      console.log('     sudo yum install ffmpeg       # RHEL/CentOS');
    }
    console.log('');
  } else {
    console.log('✓ ffmpeg is installed\n');
  }

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

  // Setup Python venv and install dependencies
  setupPythonVenv();

  // Show post-install message
  console.log(`
╔═══════════════════════════════════════════════════════════════╗
║                   Installation Complete!                      ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ${SKILL_NAME} has been installed to:                          ║
║  ${SKILL_TARGET}
║                                                               ║
║  Python venv:                                                 ║
║     ${VENV_DIR}                                               ║
║                                                               ║
║  Usage:                                                       ║
║     ${VENV_DIR}/bin/python ${SKILL_TARGET}/scripts/cli.py     ║
║                                                               ║
║  Or use the wrapper script:                                   ║
║     ${SKILL_TARGET}/scripts/eng-lang-tutor                    ║
║                                                               ║
║  Data location:                                               ║
║     ~/.openclaw/state/eng-lang-tutor/                         ║
║                                                               ║
║  Environment variables (required for TTS):                    ║
║     XUNFEI_APPID, XUNFEI_API_KEY, XUNFEI_API_SECRET           ║
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
