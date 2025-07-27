# Dell Switch Port Tracer v2.0 - OSS Team Guide

## 🎯 **OSS Team Overview**

As an **Operations Support Staff (OSS)** team member, you have **limited access** designed for day-to-day MAC address tracing operations with built-in safety protections.

![OSS Role](https://img.shields.io/badge/Role-OSS-yellow)
![Access Level](https://img.shields.io/badge/Access-Limited-orange)

---

## 🔐 **Your Access Level & Permissions**

### ✅ **What You CAN Do:**
- **MAC Address Tracing**: Find MAC addresses on access ports across all sites
- **Access Port Information**: View GigabitEthernet (Gi) and TenGigabitEthernet (Te) access ports based on switch model
- **Port Status**: See basic port configuration (access mode, VLAN assignment)
- **Site Navigation**: Browse all sites and floors in the network inventory
- **Basic Troubleshooting**: Use trace results for connectivity issues

### ❌ **What You CANNOT Do:**
- **Uplink Ports**: Cannot see uplink/trunk ports (automatically filtered)
- **Advanced VLAN Info**: Limited VLAN details for trunk/general mode ports
- **Switch Management**: No administrative access to switch configurations
- **Full Port Details**: Cannot see detailed port configurations or security settings

---

## 🌐 **Using the Web Interface**

### **Step 1: Login**
1. Navigate to the Dell Port Tracer web interface
2. Use your **Windows AD credentials** (domain\username format)
3. System will automatically assign you **OSS role** based on your AD groups

### **Step 2: Site Selection**
```
🏢 Site Selection
   ├── Main Building
   ├── Warehouse
   ├── Remote Office A
   └── Remote Office B

📍 Floor Selection (based on site)
   ├── Ground Floor
   ├── Second Floor
   └── Third Floor
```

### **Step 3: MAC Address Entry**
**Supported Formats:**
- `00:1B:63:84:45:E6` (colon-separated)
- `00-1B-63-84-45-E6` (hyphen-separated) 
- `001B.6384.45E6` (dot-separated)

### **Step 4: View Results**
Your results will show:
- **Switch Name**: Which switch contains the MAC
- **Port Number**: Specific access port (Gi1/0/24, Te1/0/12, etc.)
- **VLAN**: VLAN assignment for access ports
- **Port Mode**: Usually "access" for end devices

---

## 🔍 **Understanding Your Results**

### **Port Types You'll See:**
| Port Type | Description | Example |
|-----------|-------------|---------|
| **GigabitEthernet** | 1Gb access ports for end devices | `Gi1/0/24` |
| **TenGigabitEthernet** | 10Gb access ports (N3200 series) | `Te1/0/12` |

### **Port Information Available:**
- **Port Mode**: `access` (connects end devices)
- **VLAN ID**: Which VLAN the device is on
- **Port Description**: Human-readable port description if configured

### **What's Filtered for Your Safety:**
- **Uplink Ports**: Trunk ports connecting switches (Te, Tw, Po ports)
- **Management Interfaces**: Switch management and control interfaces
- **Security Details**: Advanced security and configuration information

---

## 🛠️ **Common Use Cases**

### **1. Desktop Connectivity Issues**
```
User Report: "My desktop can't connect to the network"
Your Process:
1. Get MAC address from user's network adapter
2. Enter MAC in Port Tracer
3. Check if MAC appears on expected switch/port
4. Verify VLAN assignment matches expected network
```

### **2. Printer/Device Location**
```
Task: "Find which port the printer is connected to"
Your Process:
1. Get printer MAC from device label or network settings
2. Trace MAC through Port Tracer
3. Identify physical switch and port location
4. Report location to requesting team
```

### **3. Network Moves**
```
Task: "User moved desks, need to verify new connection"
Your Process:
1. Get MAC address of user's device
2. Trace to confirm new port location
3. Verify VLAN matches user requirements
4. Document move completion
```

---

## 🚨 **What Different Results Mean**

### **✅ MAC Found - Normal Result**
```
Found: 00:1B:63:84:45:E6
Switch: SW-MAIN-02
Port: Gi1/0/24
VLAN: 100 (User Network)
Mode: access
```
**Action**: Device is properly connected and configured

### **❌ MAC Not Found**
```
Result: MAC address 00:1B:63:84:45:E6 not found on any switch
```
**Possible Causes**:
- Device is powered off or disconnected
- MAC address was typed incorrectly
- Device is on a different site not included in search
- Cable/port hardware issue

### **⚠️ Multiple Results** 
```
Found on multiple switches - possible MAC flapping
```
**Action**: Report to NetAdmin team - indicates potential network issue

---

## 📊 **Application Structure (Your View)**

```
Dell Port Tracer Web Interface
│
├── 🔐 Login Page
│   ├── Windows AD Authentication
│   └── Role Assignment (OSS)
│
├── 🌐 Main Dashboard
│   ├── Site Selection Dropdown
│   ├── Floor Selection Dropdown
│   ├── MAC Address Input Field
│   └── Trace Button
│
├── 📋 Results Display
│   ├── Switch Information
│   ├── Access Port Details
│   ├── VLAN Information
│   └── Port Configuration (Limited)
│
└── 🔍 Filtered Content
    ├── Only Access Ports Shown
    ├── Uplinks Hidden
    └── Basic VLAN Info Only
```

---

## 🆘 **Troubleshooting & Support**

### **Common Issues:**

**1. Can't Login**
- Verify Windows AD credentials
- Try different username formats: `domain\username` or `username@domain.com`
- Contact IT if account is locked

**2. MAC Not Found**
- Double-check MAC address format
- Verify device is powered on and connected
- Try searching different sites/floors
- Check if device uses randomized MAC addresses

**3. Slow Search Results**
- Normal for large networks (can take 30-60 seconds)
- Don't refresh page during search
- Wait for "Search Complete" message

**4. Limited Information**
- This is normal for OSS role - you see only what you need
- For more details, request NetAdmin team assistance

### **Getting Help:**
- **Technical Issues**: Contact NetAdmin team
- **Access Problems**: Submit IT help desk ticket
- **Training Questions**: Reference this guide or ask team lead

---

## 📚 **Best Practices**

### **Daily Operations:**
1. **Always verify MAC format** before searching
2. **Document results** for ticket tracking
3. **Report unusual findings** to senior staff
4. **Keep searches focused** to your assigned areas

### **Security Awareness:**
- **Never share login credentials**
- **Log out when finished** 
- **Report suspicious network activity**
- **Follow company data handling policies**

### **Efficiency Tips:**
- **Bookmark the application** for quick access
- **Use copy/paste** for MAC addresses to avoid typos
- **Search multiple sites** if device might have moved
- **Keep common device MACs** in a reference list

---

## 📞 **Team Contacts**

| Issue Type | Contact Team | Method |
|------------|--------------|---------|
| Login Problems | IT Help Desk | help@company.com |
| Network Issues | NetAdmin Team | netadmin@company.com |
| Application Bugs | Development Team | dev-support@company.com |
| Training | OSS Team Lead | oss-lead@company.com |

---

## 📈 **Your Role in Network Operations**

As an OSS team member, you are the **first line of network support**:

- **Quick Resolution**: Handle common connectivity issues efficiently
- **Accurate Reporting**: Provide precise location information for network devices
- **Safety First**: Work within your permissions to prevent network disruptions
- **Team Coordination**: Escalate complex issues to appropriate technical teams

Your limited access ensures **network stability** while giving you the tools needed for effective daily operations.

---

**Version**: 2.0.0  
**Last Updated**: January 2025  
**Team**: OSS Operations Guide
