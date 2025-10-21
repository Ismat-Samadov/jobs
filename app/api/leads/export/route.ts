/**
 * API route for exporting leads to Excel
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import pool from '@/lib/db';
import * as XLSX from 'xlsx';

/**
 * GET /api/leads/export - Export all leads to Excel
 */
export async function GET(request: NextRequest) {
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Get all leads
    const result = await pool.query(`
      SELECT
        id,
        phone_number,
        website,
        source,
        created_at,
        full_data
      FROM leads.leads
      ORDER BY created_at DESC
    `);

    // Format data for Excel - flatten full_data structure
    const data = result.rows.map(row => {
      const fullData = row.full_data || {};
      const propertyDetails = fullData.property_details || {};
      const price = fullData.price || {};
      const seller = fullData.seller || {};
      const listingInfo = fullData.listing_info || {};

      return {
        'ID': row.id,
        'Phone Number': row.phone_number,
        'Website': row.website,
        'Source URL': row.source,
        'Created At': new Date(row.created_at).toLocaleString(),

        // Property Information
        'Title': fullData.title || '',
        'Price Amount': price.amount || '',
        'Price Currency': price.currency || '',
        'Address': fullData.address || '',

        // Property Details
        'City': propertyDetails.city || '',
        'Country': propertyDetails.country || '',
        'Property Type': propertyDetails.property_type || '',
        'Category': propertyDetails.category || '',
        'Location': propertyDetails.location || '',
        'Area (m²)': propertyDetails.area_sqm || propertyDetails.area || '',
        'Area (sot)': propertyDetails.area_sot || '',
        'Rooms': propertyDetails.rooms || '',
        'Floor': propertyDetails.floor || '',
        'Document': propertyDetails.document || '',
        'Mortgage': propertyDetails.mortgage || '',
        'Repair': propertyDetails.repair || '',

        // Features
        'Features': fullData.features ? fullData.features.join(', ') : '',

        // Seller Information
        'Seller Name': seller.name || '',
        'Seller Type': seller.type || '',

        // Listing Information
        'Ad ID': listingInfo.ad_id || '',
        'Views': listingInfo.views || '',
        'Date Posted': listingInfo.date_posted || '',

        // Images
        'Number of Images': fullData.images ? fullData.images.length : 0,
        'First Image URL': fullData.images && fullData.images.length > 0 ? fullData.images[0] : '',

        // Description
        'Description': fullData.description || '',
      };
    });

    // Create workbook and worksheet
    const workbook = XLSX.utils.book_new();
    const worksheet = XLSX.utils.json_to_sheet(data);

    // Set column widths
    worksheet['!cols'] = [
      { wch: 8 },   // ID
      { wch: 15 },  // Phone Number
      { wch: 15 },  // Website
      { wch: 50 },  // Source URL
      { wch: 20 },  // Created At
      { wch: 50 },  // Title
      { wch: 15 },  // Price Amount
      { wch: 10 },  // Price Currency
      { wch: 50 },  // Address
      { wch: 15 },  // City
      { wch: 15 },  // Country
      { wch: 20 },  // Property Type
      { wch: 20 },  // Category
      { wch: 30 },  // Location
      { wch: 12 },  // Area (m²)
      { wch: 12 },  // Area (sot)
      { wch: 10 },  // Rooms
      { wch: 10 },  // Floor
      { wch: 20 },  // Document
      { wch: 12 },  // Mortgage
      { wch: 15 },  // Repair
      { wch: 50 },  // Features
      { wch: 20 },  // Seller Name
      { wch: 20 },  // Seller Type
      { wch: 12 },  // Ad ID
      { wch: 10 },  // Views
      { wch: 15 },  // Date Posted
      { wch: 12 },  // Number of Images
      { wch: 60 },  // First Image URL
      { wch: 100 }, // Description
    ];

    XLSX.utils.book_append_sheet(workbook, worksheet, 'Leads');

    // Generate buffer
    const buffer = XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' });

    // Return as downloadable file
    const filename = `leads_export_${new Date().toISOString().split('T')[0]}.xlsx`;

    return new NextResponse(buffer, {
      headers: {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    console.error('Error exporting leads:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
