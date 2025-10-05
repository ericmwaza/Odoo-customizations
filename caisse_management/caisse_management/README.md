# Caisse Management Module

A comprehensive cash advance and expense management system for Odoo 18.

## Overview

The Caisse Management module provides a complete solution for managing cash advances, petty cash, and other expense disbursements within your organization. It includes approval workflows, real-time accounting integration, and detailed audit trails.

## Key Features

### 🔄 Workflow Management
- **Request Submission**: Employees can request salary advances, petty cash, or expense funds
- **Manager Approval**: Configurable approval limits and workflow routing
- **Cashier Disbursement**: Secure fund disbursement with payment method tracking
- **Settlement Tracking**: Automatic settlement deadlines and overdue monitoring

### 📊 Accounting Integration
- **Real-time Posting**: Automatic journal entries upon disbursement
- **Analytical Tracking**: Link transactions to analytical accounts
- **Journal Management**: Dedicated cash journals for caisse operations
- **Balance Monitoring**: Real-time balance tracking and limits

### 🔐 Security & Controls
- **Role-based Access**: Employee, Manager, Cashier, and Administrator roles
- **Approval Limits**: Configurable limits for managers and cashiers
- **Daily Limits**: Maximum daily disbursement controls
- **Audit Trail**: Complete history of all operations

### 📈 Reporting & Reconciliation
- **Dashboard Views**: Role-specific dashboards for cashiers and managers
- **Reconciliation Tools**: Daily, weekly, and monthly reconciliation
- **Outstanding Reports**: Track pending settlements and overdue advances
- **Summary Reports**: Comprehensive activity and balance reports

## Installation

1. Copy the module to your Odoo addons directory
2. Update the module list in Odoo
3. Install the "Caisse Management" module

## Dependencies

- `base`
- `account`
- `hr`
- `analytic`

## Configuration

### Initial Setup

1. **Configure Caisse Settings**:
   - Go to Caisse > Configuration > Caisse Configuration
   - Set up your cash journal and accounts
   - Configure approval limits and workflow settings

2. **Set Up User Roles**:
   - Assign users to appropriate groups:
     - Caisse Employee: Can create requests
     - Caisse Manager: Can approve requests
     - Caisse Cashier: Can disburse funds
     - Caisse Administrator: Full configuration access

3. **Configure Accounts**:
   - Employee Advance Account: For tracking advances
   - Petty Cash Expense Account: For petty cash expenses
   - Default Analytical Account: For expense tracking

## Usage

### For Employees
1. Navigate to Caisse > Operations > Fund Requests
2. Create a new request with type, amount, and description
3. Submit for approval
4. Track status and settlement deadlines

### For Managers
1. Use Manager Dashboard for overview
2. Review pending requests in "Requests to Approve"
3. Approve or reject requests with comments
4. Monitor outstanding advances and overdue settlements

### For Cashiers
1. Use Cashier Dashboard for daily operations
2. Process approved requests for disbursement
3. Choose payment method (cash, bank transfer, check)
4. Perform daily/weekly reconciliations
5. Track cash denominations and variances

## Workflow States

### Request States
- **Draft**: Initial state, can be edited
- **Submitted**: Pending manager approval
- **Manager Approved**: Ready for disbursement
- **Rejected**: Declined by manager
- **Disbursed**: Funds have been released
- **Settled**: Advance has been settled (for advances only)
- **Cancelled**: Request cancelled

### Disbursement States
- **Draft**: Prepared but not yet disbursed
- **Disbursed**: Funds released and accounting entries created
- **Cancelled**: Disbursement cancelled

### Reconciliation States
- **Draft**: In progress
- **Reconciled**: Completed by cashier
- **Closed**: Approved and closed by supervisor

## Reports

### Available Reports
1. **Caisse Summary Report**: Overview of configuration and recent activity
2. **Disbursements Report**: Detailed disbursement listing
3. **Reconciliation Report**: Complete reconciliation details with variances
4. **Outstanding Advances Report**: Pending settlements and overdue advances

### Accessing Reports
- Navigate to Caisse > Reports
- Select desired report type
- Generate PDF reports for printing or archiving

## Security

### User Groups
- **Caisse Employee**: Basic access for request creation
- **Caisse Manager**: Approval rights and oversight
- **Caisse Cashier**: Disbursement and reconciliation rights
- **Caisse Administrator**: Full configuration access

### Record Rules
- Employees can only see their own requests
- Managers can see all requests for approval
- Cashiers can see approved requests for disbursement
- Administrators have full access to all records

## Technical Details

### Models
- `caisse.config`: Configuration settings
- `caisse.request`: Fund requests with workflow
- `caisse.disbursement`: Cash disbursement records
- `caisse.reconciliation`: Reconciliation periods
- `caisse.reconciliation.denomination`: Cash denomination tracking

### Accounting Integration
- Automatic journal entry creation upon disbursement
- Configurable debit/credit accounts based on request type
- Analytical account integration for expense tracking
- Real-time balance calculation from journal entries

## Troubleshooting

### Common Issues

1. **Configuration Missing**:
   - Ensure caisse configuration is properly set up
   - Check journal and account settings

2. **Permission Errors**:
   - Verify user group assignments
   - Check record rules and access rights

3. **Accounting Entries Not Created**:
   - Verify "Auto Create Accounting Entries" is enabled
   - Check journal and account configuration
   - Ensure proper permissions for account moves

4. **Limits Not Working**:
   - Review approval limit settings
   - Check daily disbursement limits
   - Verify manager approval requirements

## Support

For issues or questions:
- Check the module documentation
- Review Odoo logs for error details
- Contact the module author: ericmwaza@gmail.com

## Version History

- **18.0.1.0.0**: Initial release for Odoo 18
  - Complete workflow implementation
  - Accounting integration
  - Role-based security
  - Reporting and reconciliation features

## License

AGPL-3

## Author

Eric Mwaza (ericmwaza@gmail.com)