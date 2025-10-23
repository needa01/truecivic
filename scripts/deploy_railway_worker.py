#!/usr/bin/env python3
"""
Railway Worker Deployment Helper Script

This script helps you:
1. Verify all prerequisites are met
2. Test Prefect API connection
3. Deploy flows to Railway
4. Monitor initial flow runs

Usage:
    python scripts/deploy_railway_worker.py --check-prerequisites
    python scripts/deploy_railway_worker.py --deploy-flows
    python scripts/deploy_railway_worker.py --test-worker
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import httpx
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

PREFECT_API_URL = "https://prefect-production-a5a7.up.railway.app/api"
RAILWAY_WORKER_NAME = "railway-worker"
WORK_POOL_NAME = "default-agent-pool"

# ============================================================================
# Prerequisite Checks
# ============================================================================

def check_prerequisites() -> bool:
    """Check if all prerequisites are met for Railway worker deployment."""
    logger.info("Checking prerequisites...")
    
    checks_passed = 0
    checks_total = 5
    
    # Check 1: Python version
    if sys.version_info >= (3, 9):
        logger.info("✅ Python 3.9+ installed")
        checks_passed += 1
    else:
        logger.error(f"❌ Python 3.9+ required (found {sys.version_info.major}.{sys.version_info.minor})")
    
    # Check 2: Prefect installed
    try:
        result = subprocess.run(
            ["prefect", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            logger.info(f"✅ Prefect installed: {version}")
            checks_passed += 1
        else:
            logger.error("❌ Prefect not installed or not in PATH")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"❌ Prefect check failed: {e}")
    
    # Check 3: railway-worker.dockerfile exists
    if Path("railway-worker.dockerfile").exists():
        logger.info("✅ railway-worker.dockerfile exists")
        checks_passed += 1
    else:
        logger.error("❌ railway-worker.dockerfile not found")
    
    # Check 4: prefect.yaml exists
    if Path("prefect.yaml").exists():
        logger.info("✅ prefect.yaml exists")
        checks_passed += 1
    else:
        logger.error("❌ prefect.yaml not found")
    
    # Check 5: requirements.txt includes prefect
    try:
        with open("requirements.txt", "r") as f:
            content = f.read()
            if "prefect" in content.lower():
                logger.info("✅ requirements.txt includes prefect")
                checks_passed += 1
            else:
                logger.error("❌ requirements.txt missing prefect dependency")
    except FileNotFoundError:
        logger.error("❌ requirements.txt not found")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Prerequisite Checks: {checks_passed}/{checks_total} passed")
    logger.info(f"{'='*60}\n")
    
    return checks_passed == checks_total


# ============================================================================
# Prefect API Tests
# ============================================================================

async def test_prefect_connection() -> bool:
    """Test connection to Prefect API."""
    logger.info(f"Testing connection to Prefect API: {PREFECT_API_URL}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PREFECT_API_URL}/health",
                timeout=10.0
            )
            
            if response.status_code == 200:
                logger.info("✅ Connected to Prefect Server")
                return True
            else:
                logger.error(f"❌ Prefect API returned {response.status_code}")
                return False
    
    except Exception as e:
        logger.error(f"❌ Failed to connect to Prefect API: {e}")
        return False


def get_prefect_status() -> Optional[dict]:
    """Get Prefect configuration and work pool information."""
    logger.info("Fetching Prefect configuration...")
    
    try:
        result = subprocess.run(
            ["prefect", "config", "view"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info("✅ Prefect configuration retrieved")
            logger.info(result.stdout)
            return {"status": "ok"}
        else:
            logger.error(f"❌ Failed to get Prefect config: {result.stderr}")
            return None
    
    except Exception as e:
        logger.error(f"❌ Error getting Prefect status: {e}")
        return None


def check_work_pool() -> bool:
    """Check if work pool exists."""
    logger.info(f"Checking for work pool: {WORK_POOL_NAME}")
    
    try:
        result = subprocess.run(
            ["prefect", "work-pool", "ls"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and WORK_POOL_NAME in result.stdout:
            logger.info(f"✅ Work pool '{WORK_POOL_NAME}' exists")
            return True
        else:
            logger.warning(f"⚠️  Work pool '{WORK_POOL_NAME}' not found")
            logger.info("You may need to create it manually:")
            logger.info(f"  prefect work-pool create {WORK_POOL_NAME}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error checking work pool: {e}")
        return False


# ============================================================================
# Deployment Functions
# ============================================================================

def deploy_flows() -> bool:
    """Deploy all flows to Prefect."""
    logger.info("Deploying flows to Prefect...")
    
    # Set Prefect API URL
    env = os.environ.copy()
    env["PREFECT_API_URL"] = PREFECT_API_URL
    
    try:
        result = subprocess.run(
            ["prefect", "deploy", "--all"],
            env=env,
            timeout=60
        )
        
        if result.returncode == 0:
            logger.info("✅ Flows deployed successfully")
            return True
        else:
            logger.error("❌ Flow deployment failed")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error deploying flows: {e}")
        return False


def list_deployments() -> bool:
    """List all deployed flows."""
    logger.info("Listing deployed flows...")
    
    env = os.environ.copy()
    env["PREFECT_API_URL"] = PREFECT_API_URL
    
    try:
        result = subprocess.run(
            ["prefect", "deployment", "ls"],
            env=env,
            timeout=30
        )
        
        return result.returncode == 0
    
    except Exception as e:
        logger.error(f"❌ Error listing deployments: {e}")
        return False


# ============================================================================
# Testing & Monitoring
# ============================================================================

def test_worker_connection() -> bool:
    """Test if worker can connect and get tasks."""
    logger.info("Testing worker connection to Prefect...")
    logger.info("This requires the worker to be running on Railway")
    logger.info("Check Railway dashboard → prefect-worker → Logs")
    
    logger.info("\n✅ Worker testing:")
    logger.info("  1. Go to https://railway.app/dashboard")
    logger.info("  2. Select prefect-worker service")
    logger.info("  3. Check Logs tab for:")
    logger.info("     'Connected to Prefect Server'")
    logger.info("     'Polling for flow runs'")
    
    return True


def trigger_test_flow() -> bool:
    """Trigger a test flow run."""
    logger.info("Triggering test flow run...")
    
    env = os.environ.copy()
    env["PREFECT_API_URL"] = PREFECT_API_URL
    
    try:
        result = subprocess.run(
            ["prefect", "deployment", "run", "fetch-bills-hourly"],
            env=env,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info("✅ Test flow triggered")
            logger.info("Monitor in Prefect UI: https://prefect-production-a5a7.up.railway.app")
            return True
        else:
            logger.error("❌ Failed to trigger test flow")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error triggering test flow: {e}")
        return False


# ============================================================================
# Main Functions
# ============================================================================

def print_banner():
    """Print banner."""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║          Railway Worker Deployment Helper                         ║
║                                                                    ║
║  Helps deploy Prefect worker to Railway for production ETL       ║
╚════════════════════════════════════════════════════════════════════╝
    """)


def print_next_steps():
    """Print next steps after deployment."""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║  Next Steps                                                        ║
╚════════════════════════════════════════════════════════════════════╝

1. GO TO RAILWAY DASHBOARD
   └─ https://railway.app/dashboard

2. CONFIGURE WORKER SERVICE
   ├─ Service Type: Change to "Worker Service"
   ├─ Dockerfile: railway-worker.dockerfile
   ├─ Start Command: prefect worker start --pool default-agent-pool --name railway-worker
   └─ Environment: Set PREFECT_API_URL, DATABASE_PUBLIC_URL, REDIS_URL

3. DEPLOY TO RAILWAY
   └─ Click Deploy button (auto-deploys on save)

4. VERIFY WORKER RUNNING
   ├─ Go to prefect-worker service → Logs
   └─ Look for: "Polling for flow runs..."

5. DEPLOY FLOWS FROM LOCAL MACHINE
   ├─ Set PREFECT_API_URL environment variable
   ├─ Run: prefect deploy --all
   └─ Verify: prefect deployment ls

6. TEST END-TO-END
   ├─ Manually trigger: prefect deployment run fetch-bills-hourly
   ├─ Monitor: Prefect UI or Railway logs
   └─ Verify: Data in database

For detailed instructions, see: docs/RAILWAY_WORKER_DEPLOYMENT.md
    """)


# ============================================================================
# CLI
# ============================================================================

def main():
    """Main entry point."""
    print_banner()
    
    import argparse
    parser = argparse.ArgumentParser(
        description="Railway Worker Deployment Helper"
    )
    parser.add_argument(
        "--check-prerequisites",
        action="store_true",
        help="Check if prerequisites are met"
    )
    parser.add_argument(
        "--deploy-flows",
        action="store_true",
        help="Deploy flows to Prefect"
    )
    parser.add_argument(
        "--test-worker",
        action="store_true",
        help="Test worker connection"
    )
    parser.add_argument(
        "--trigger-test",
        action="store_true",
        help="Trigger a test flow run"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all checks and deployments"
    )
    
    args = parser.parse_args()
    
    # If no arguments, show help
    if not any([args.check_prerequisites, args.deploy_flows, args.test_worker, args.trigger_test, args.all]):
        parser.print_help()
        print_next_steps()
        return
    
    # Run checks
    if args.check_prerequisites or args.all:
        if not check_prerequisites():
            logger.error("❌ Prerequisites not met. Aborting.")
            return
    
    # Check work pool
    if args.deploy_flows or args.all:
        check_work_pool()
    
    # Deploy flows
    if args.deploy_flows or args.all:
        if not deploy_flows():
            logger.error("❌ Deployment failed")
            return
        
        list_deployments()
    
    # Test worker
    if args.test_worker or args.all:
        test_worker_connection()
    
    # Trigger test flow
    if args.trigger_test:
        trigger_test_flow()
    
    print_next_steps()


if __name__ == "__main__":
    main()
