# SS Empire Payment Gateway & UPI Checkout Engine

A high-performance, modern UPI Payment Gateway and Checkout Web Application designed for seamless merchant payment processing, real-time banking verification, and webhook notifications.

---

## 🌟 Key Features

1. **Dynamic UPI QR & Deep-linking**:
   - Generates instant NPCI-compliant dynamic QR codes with locked transaction amounts and order IDs.
   - 1-tap app launch buttons for Google Pay, PhonePe, Paytm, and BHIM UPI.
   - Real-time 10-minute order session countdown timer.

2. **Dual Gateway Engine**:
   - **Direct UPI Engine**: 100% peer-to-peer instant settlement directly to merchant bank account with zero fees.
   - **TerminalX / Merchant API Engine**: Automated transaction verification and bank reconciliation.

3. **Instant Verification & Notifications**:
   - 12-digit Bank UTR confirmation interface.
   - Automatic Discord webhook announcements with verified payment proof embeds.
   - Configurable outgoing webhook dispatch for ecommerce and SaaS platforms.

4. **Security & Compliance**:
   - Zero-dependency static frontend with responsive glassmorphism UI.
   - Safe session management and authenticated administrative panel.
   - Optimized for cloud platforms (Vercel, Render, AWS, Docker).

---

## 🚀 Deployment

### Deploy on Vercel
1. Import this repository into your Vercel account.
2. The `vercel.json` and `@vercel/python` builder will automatically configure the serverless endpoints.
3. Click **Deploy**.

### Local Launch
```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python app.py
```
Open `http://127.0.0.1:5000` in your web browser.

---

## 📄 License
MIT License. Created by SS Empire.
