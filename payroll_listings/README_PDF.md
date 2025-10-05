# Custom ReportLab PDF Generation

This module now uses **ReportLab** instead of Odoo's built-in PDF system for better landscape support and precise logo positioning.

## Installation

1. **Install ReportLab**:
   ```bash
   pip install reportlab>=3.6.0
   ```
   Or use the requirements file:
   ```bash
   pip install -r requirements.txt
   ```

2. **Restart Odoo** after installation

3. **Update the module** in Odoo

## Features

✅ **True Landscape Orientation** - A3 landscape (420mm × 297mm)  
✅ **Logo in Top-Left Corner** - Precise positioning (60mm × 30mm)  
✅ **Wide Table Support** - Handles 15+ columns without cramping  
✅ **Professional Formatting** - Custom styles and colors  
✅ **All Report Types** - Works with all 50+ report types  

## How It Works

1. User clicks "GÉNERER" and selects "PDF"
2. Custom ReportLab controller generates landscape PDF
3. Browser downloads the properly formatted PDF
4. Logo appears in top-left, tables fit perfectly in landscape

## Technical Details

- **Controller**: `/payroll/pdf/generate`
- **Page Size**: A3 Landscape (420mm × 297mm)
- **Margins**: 15mm on all sides
- **Logo Size**: 60mm × 30mm (top-left corner)
- **Font Sizes**: Adaptive (8px-11px based on column count)
- **Table Styling**: Professional colors and borders