# Optima Payment

**Optima Payment** is a comprehensive application designed to streamline financial workflows for businesses. It simplifies the management of **post-dated cheques (PDC)**, **company expenses**, and **bank guarantee letters** ensuring accurate and efficient handling of essential financial operations. With its user-friendly interface and robust feature set, Optima Payment is a perfect solution for businesses of all sizes, particularly in the Saudi Arabian market.

---

## 🚀 Main Features

Optima Payment enhances financial processes with the following features:

### **Cheque Lifecycle Management**
- **Customer Cheques:**
  - Record receipt of cheques from customers.
  - Deposit cheques into the "Under Collection" portfolio.
  - Clear cheques in the bank.
  - Return cheques to customers in case of rejection.
- **Supplier Cheques:**
  - Issue cheques to suppliers.
  - Endorse cheques to suppliers.
  - Clear supplier cheques in the bank on their due date.

### **Company Expenses**
- Easily manage non-taxable company and petty cash expenses.
- Generate a single payment entry for multiple petty cash expenses.
- Link purchase invoices with expense claims in the system.

### **Bank Guarantee Letters**
- Handle the lifecycle of bank guarantee letters efficiently.
- Generate accurate journal entries for every workflow related to bank guarantees.
- Access a detailed **Bank Guarantee Report** to monitor guarantees.

### **Custom Cheque Printing**
- Print cheques directly from the system.
- Supports over **40 official cheque templates**.
- Add new cheque templates as needed.

### **Cheque Tracking and Reporting**
- Detailed tracking of all cheques and their statuses.
- Generate comprehensive reports to monitor cheque lifecycles in real-time.

---

## 💡 Why Choose Optima Payment?

1. **Comprehensive Features:** Covers all aspects of cheque management, company expenses, and bank guarantee letters.
2. **Ease of Use:** Intuitive workflows and user-friendly interface.
3. **Customizable:** Flexible settings for cheque templates and workflows.
4. **Detailed Reporting:** Gain full visibility of cheque and expense statuses.
5. **Scalable:** Perfect for businesses of all sizes.

---

## 📦 Installation

Follow these steps to install Optima Payment on your ERPNext setup:

1. Clone the repository:
   ```bash
   bench get-app https://github.com/itsystematic/optima_payment.git
   ```
2. Install requirements:
   ```bash
   bench setup requirements
   ```
3. Build the app:
   ```bash
   bench build --app optima_payment
   ```
4. Restart the bench:
   ```bash
   bench restart
   ```
5. Install the app on your site:
   ```bash
   bench --site [your.site.name] install-app optima_payment
   ```
6. Run migrations:
   ```bash
   bench --site [your.site.name] migrate
   ```

---

## 🛠️ How to Use

Optima Payment is designed to be simple and intuitive. Refer to our **[Youtube channel](https://www.youtube.com/@itsystematic)** for detailed instructions. or contact support for assistance.

### Supported ERPNext Versions
- ERPNext Version 15

---

## 📞 Support

We offer comprehensive support to ensure you have the best experience with Optima Payment:

- For premium support or paid feature requests, email us at:  
  **support@itsystematic.com**

### **Issue Reporting**
- Found a bug or need a new feature? Create an issue after checking existing ones:  
  [GitHub Issues](https://github.com/itsystematic/optima_payment/issues)

---

## 🤝 Contributing

We welcome contributions from the community! Please follow the contribution guidelines outlined in our Contributing Guide.

### Guidelines
- Submit issues through GitHub Issues.
- Follow best practices for pull requests.
- Ensure proper testing before submitting.

---

## 📜 License

Optima Payment is licensed under the **MIT License**. See the full license in the [LICENSE](https://github.com/itsystematic/optima_payment/blob/main/license.txt) file.

---

## 📂 More Apps by IT Systematic

Explore other powerful apps developed by IT Systematic:

- **[Optima ZATCA](https://github.com/itsystematic/optima_zatca):** A comprehensive app for managing ZATCA compliance in Saudi Arabia.
- **[Optima HR](https://github.com/itsystematic/optima-hr):** Transform HR operations with a powerful ERPNext-powered solution.
