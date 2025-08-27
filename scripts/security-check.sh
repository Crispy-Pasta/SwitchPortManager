#!/bin/bash
# Security Check Script - Dell Switch Port Tracer
# Identifies potentially sensitive files that shouldn't be committed to Git

echo "🔍 Dell Switch Port Tracer - Security File Check"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

SECURITY_ISSUES=0

# Function to check for sensitive files
check_sensitive_files() {
    echo "🔒 Checking for sensitive files..."
    
    # Check for environment files with actual content
    if [ -f .env ] && [ -s .env ]; then
        echo -e "${RED}❌ WARNING: .env file exists and contains data${NC}"
        echo "   This file may contain sensitive credentials"
        echo "   File size: $(du -h .env | cut -f1)"
        SECURITY_ISSUES=$((SECURITY_ISSUES + 1))
    elif [ -f .env ]; then
        echo -e "${YELLOW}⚠️  .env file exists but is empty${NC}"
    else
        echo -e "${GREEN}✅ No .env file found${NC}"
    fi
    
    # Check for other environment files
    ENV_FILES=(
        ".env.production"
        ".env.staging" 
        ".env.local"
        ".environment"
        "config.txt"
        "settings.txt"
    )
    
    for file in "${ENV_FILES[@]}"; do
        if [ -f "$file" ]; then
            echo -e "${RED}❌ WARNING: $file exists${NC}"
            SECURITY_ISSUES=$((SECURITY_ISSUES + 1))
        fi
    done
    
    # Check for credential-related files
    CREDENTIAL_PATTERNS=(
        "*secret*"
        "*SECRET*" 
        "*password*"
        "*PASSWORD*"
        "*credential*"
        "*.key"
        "*.pem"
    )
    
    echo ""
    echo "🔑 Checking for credential files..."
    FOUND_CREDENTIALS=false
    
    for pattern in "${CREDENTIAL_PATTERNS[@]}"; do
        for file in $pattern; do
            if [ -f "$file" ] && [ "$file" != "*" ]; then
                echo -e "${RED}❌ WARNING: Credential file found: $file${NC}"
                SECURITY_ISSUES=$((SECURITY_ISSUES + 1))
                FOUND_CREDENTIALS=true
            fi
        done
    done
    
    if [ "$FOUND_CREDENTIALS" = false ]; then
        echo -e "${GREEN}✅ No credential files found${NC}"
    fi
}

# Function to check for database files
check_database_files() {
    echo ""
    echo "🗄️ Checking for database files..."
    
    DB_FILES=(
        "*.db"
        "*.sqlite"
        "*.sqlite3"
        "complete_migration.sql"
        "*_migration*.sql"
    )
    
    FOUND_DB=false
    for pattern in "${DB_FILES[@]}"; do
        for file in $pattern; do
            if [ -f "$file" ] && [ "$file" != "*" ]; then
                echo -e "${RED}❌ WARNING: Database file found: $file${NC}"
                SECURITY_ISSUES=$((SECURITY_ISSUES + 1))
                FOUND_DB=true
            fi
        done
    done
    
    if [ "$FOUND_DB" = false ]; then
        echo -e "${GREEN}✅ No database files found${NC}"
    fi
}

# Function to check git status for untracked sensitive files
check_git_status() {
    echo ""
    echo "📋 Checking Git status for untracked files..."
    
    # Get list of untracked files
    UNTRACKED=$(git ls-files --others --exclude-standard)
    
    if [ -z "$UNTRACKED" ]; then
        echo -e "${GREEN}✅ No untracked files${NC}"
        return
    fi
    
    # Check if untracked files match sensitive patterns
    echo "Untracked files found:"
    for file in $UNTRACKED; do
        SENSITIVE=false
        
        # Check against sensitive patterns
        if [[ $file =~ \.(env|key|pem|p12|pfx|db|sqlite|backup|dump)$ ]] || \
           [[ $file =~ (secret|password|credential|config\.txt|settings\.txt) ]]; then
            echo -e "${RED}❌ SENSITIVE: $file${NC}"
            SECURITY_ISSUES=$((SECURITY_ISSUES + 1))
            SENSITIVE=true
        fi
        
        if [ "$SENSITIVE" = false ]; then
            echo -e "${YELLOW}📄 $file${NC}"
        fi
    done
}

# Function to check .gitignore coverage
check_gitignore_coverage() {
    echo ""
    echo "🛡️ Checking .gitignore coverage..."
    
    if [ ! -f .gitignore ]; then
        echo -e "${RED}❌ WARNING: No .gitignore file found!${NC}"
        SECURITY_ISSUES=$((SECURITY_ISSUES + 1))
        return
    fi
    
    # Check for essential patterns
    REQUIRED_PATTERNS=(
        ".env"
        "*.log"
        "__pycache__"
        "*.key"
        "*.db"
        "*secret*"
        "*password*"
    )
    
    MISSING_PATTERNS=()
    for pattern in "${REQUIRED_PATTERNS[@]}"; do
        if ! grep -q "$pattern" .gitignore; then
            MISSING_PATTERNS+=("$pattern")
        fi
    done
    
    if [ ${#MISSING_PATTERNS[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ .gitignore has good security coverage${NC}"
    else
        echo -e "${YELLOW}⚠️  .gitignore missing patterns:${NC}"
        for pattern in "${MISSING_PATTERNS[@]}"; do
            echo "   - $pattern"
        done
    fi
}

# Main execution
check_sensitive_files
check_database_files
check_git_status
check_gitignore_coverage

echo ""
echo "================================================"
if [ $SECURITY_ISSUES -eq 0 ]; then
    echo -e "${GREEN}🎉 Security Check PASSED: No sensitive files detected${NC}"
    echo ""
    echo "✅ Repository is secure for Git operations"
else
    echo -e "${RED}⚠️  Security Check FAILED: $SECURITY_ISSUES security issues found${NC}"
    echo ""
    echo "🔧 Recommended actions:"
    echo "1. Review and remove/secure any sensitive files identified above"
    echo "2. Add sensitive patterns to .gitignore"
    echo "3. Use .env.example for template, never commit actual .env"
    echo "4. Re-run this script until all issues are resolved"
fi

echo ""
echo "💡 Security Best Practices:"
echo "- Always use .env.example as template"
echo "- Never commit actual credentials or API keys"
echo "- Use environment variables for production secrets"
echo "- Regularly audit repository for sensitive data"

exit $SECURITY_ISSUES
