/**
 * API routes for folder operations
 */
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';
import pool from '@/lib/db';

export const dynamic = 'force-dynamic';

/**
 * GET /api/folders - Get all folders with hierarchy
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

    const query = `
      WITH RECURSIVE folder_tree AS (
        -- Base case: root folders
        SELECT
          id,
          name,
          parent_id,
          created_at,
          0 as depth,
          ARRAY[id] as path
        FROM leads.folders
        WHERE parent_id IS NULL

        UNION ALL

        -- Recursive case: child folders
        SELECT
          f.id,
          f.name,
          f.parent_id,
          f.created_at,
          ft.depth + 1,
          ft.path || f.id
        FROM leads.folders f
        INNER JOIN folder_tree ft ON f.parent_id = ft.id
      )
      SELECT
        ft.*,
        u.username as created_by_username,
        (SELECT COUNT(*) FROM leads.files WHERE folder_id = ft.id) as file_count,
        (SELECT COUNT(*) FROM leads.folders WHERE parent_id = ft.id) as subfolder_count
      FROM folder_tree ft
      LEFT JOIN users u ON ft.id IN (SELECT id FROM leads.folders WHERE created_by = u.id)
      ORDER BY ft.depth, ft.name
    `;

    const result = await pool.query(query);

    return NextResponse.json({ folders: result.rows });
  } catch (error) {
    console.error('Error fetching folders:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

/**
 * POST /api/folders - Create a new folder (Admin only)
 */
export async function POST(request: NextRequest) {
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token || token.role !== 'admin') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { name, parent_id } = body;

    if (!name || name.trim() === '') {
      return NextResponse.json({ error: 'Folder name is required' }, { status: 400 });
    }

    // Check if folder with same name already exists in parent
    const checkQuery = `
      SELECT id FROM leads.folders
      WHERE name = $1 AND parent_id ${parent_id ? '= $2' : 'IS NULL'}
    `;

    const checkParams = parent_id ? [name.trim(), parent_id] : [name.trim()];
    const checkResult = await pool.query(checkQuery, checkParams);

    if (checkResult.rows.length > 0) {
      return NextResponse.json(
        { error: 'A folder with this name already exists in this location' },
        { status: 400 }
      );
    }

    const insertQuery = `
      INSERT INTO leads.folders (name, parent_id, created_by)
      VALUES ($1, $2, $3)
      RETURNING *
    `;

    const values = [name.trim(), parent_id || null, token.sub];

    const result = await pool.query(insertQuery, values);

    return NextResponse.json({
      message: 'Folder created successfully',
      folder: result.rows[0],
    });
  } catch (error) {
    console.error('Error creating folder:', error);
    return NextResponse.json({ error: 'Failed to create folder' }, { status: 500 });
  }
}

/**
 * PUT /api/folders - Update folder (rename or move) (Admin only)
 */
export async function PUT(request: NextRequest) {
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token || token.role !== 'admin') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { id, name, parent_id } = body;

    if (!id) {
      return NextResponse.json({ error: 'Folder ID is required' }, { status: 400 });
    }

    // Check if folder exists
    const folderCheck = await pool.query('SELECT * FROM leads.folders WHERE id = $1', [id]);

    if (folderCheck.rows.length === 0) {
      return NextResponse.json({ error: 'Folder not found' }, { status: 404 });
    }

    // Prevent moving folder into itself or its descendants
    if (parent_id) {
      const isDescendant = await checkIfDescendant(id, parent_id);
      if (isDescendant || id === parent_id) {
        return NextResponse.json(
          { error: 'Cannot move a folder into itself or its descendants' },
          { status: 400 }
        );
      }
    }

    // Check for duplicate name in target location
    if (name) {
      const targetParentId = parent_id !== undefined ? parent_id : folderCheck.rows[0].parent_id;
      const checkQuery = `
        SELECT id FROM leads.folders
        WHERE name = $1 AND id != $2 AND parent_id ${targetParentId ? '= $3' : 'IS NULL'}
      `;

      const checkParams = targetParentId
        ? [name.trim(), id, targetParentId]
        : [name.trim(), id];

      const dupCheck = await pool.query(checkQuery, checkParams);

      if (dupCheck.rows.length > 0) {
        return NextResponse.json(
          { error: 'A folder with this name already exists in the target location' },
          { status: 400 }
        );
      }
    }

    // Build update query dynamically
    const updates: string[] = [];
    const values: any[] = [];
    let paramIndex = 1;

    if (name !== undefined) {
      updates.push(`name = $${paramIndex}`);
      values.push(name.trim());
      paramIndex++;
    }

    if (parent_id !== undefined) {
      updates.push(`parent_id = $${paramIndex}`);
      values.push(parent_id || null);
      paramIndex++;
    }

    if (updates.length === 0) {
      return NextResponse.json({ error: 'No updates provided' }, { status: 400 });
    }

    values.push(id);

    const updateQuery = `
      UPDATE leads.folders
      SET ${updates.join(', ')}
      WHERE id = $${paramIndex}
      RETURNING *
    `;

    const result = await pool.query(updateQuery, values);

    return NextResponse.json({
      message: 'Folder updated successfully',
      folder: result.rows[0],
    });
  } catch (error) {
    console.error('Error updating folder:', error);
    return NextResponse.json({ error: 'Failed to update folder' }, { status: 500 });
  }
}

/**
 * DELETE /api/folders - Delete a folder (Admin only)
 * Query params:
 *   - id: Folder ID to delete
 *   - force: If 'true', delete folder with all contents (files and subfolders)
 */
export async function DELETE(request: NextRequest) {
  try {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token || token.role !== 'admin') {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');
    const force = searchParams.get('force') === 'true';

    if (!id) {
      return NextResponse.json({ error: 'Folder ID is required' }, { status: 400 });
    }

    // Check if folder exists
    const folderCheck = await pool.query('SELECT * FROM leads.folders WHERE id = $1', [id]);

    if (folderCheck.rows.length === 0) {
      return NextResponse.json({ error: 'Folder not found' }, { status: 404 });
    }

    // Check if folder has files or subfolders
    const contentCheck = await pool.query(
      `
      SELECT
        (SELECT COUNT(*) FROM leads.files WHERE folder_id = $1) as file_count,
        (SELECT COUNT(*) FROM leads.folders WHERE parent_id = $1) as subfolder_count
      `,
      [id]
    );

    const { file_count, subfolder_count } = contentCheck.rows[0];

    if (parseInt(file_count) > 0 || parseInt(subfolder_count) > 0) {
      if (!force) {
        return NextResponse.json(
          {
            error: 'Cannot delete folder with contents',
            details: `Folder contains ${file_count} file(s) and ${subfolder_count} subfolder(s)`,
          },
          { status: 400 }
        );
      }

      // Force delete: Delete all files in folder first
      if (parseInt(file_count) > 0) {
        await pool.query('DELETE FROM leads.files WHERE folder_id = $1', [id]);
      }

      // Force delete: Recursively delete all subfolders
      if (parseInt(subfolder_count) > 0) {
        const deleteSubfoldersQuery = `
          WITH RECURSIVE folder_tree AS (
            SELECT id FROM leads.folders WHERE parent_id = $1
            UNION ALL
            SELECT f.id FROM leads.folders f
            INNER JOIN folder_tree ft ON f.parent_id = ft.id
          )
          DELETE FROM leads.files WHERE folder_id IN (SELECT id FROM folder_tree);

          WITH RECURSIVE folder_tree AS (
            SELECT id FROM leads.folders WHERE parent_id = $1
            UNION ALL
            SELECT f.id FROM leads.folders f
            INNER JOIN folder_tree ft ON f.parent_id = ft.id
          )
          DELETE FROM leads.folders WHERE id IN (SELECT id FROM folder_tree);
        `;
        await pool.query(deleteSubfoldersQuery, [id]);
      }
    }

    // Delete folder
    await pool.query('DELETE FROM leads.folders WHERE id = $1', [id]);

    return NextResponse.json({
      message: 'Folder deleted successfully',
      deleted: {
        files: parseInt(file_count),
        subfolders: parseInt(subfolder_count)
      }
    });
  } catch (error) {
    console.error('Error deleting folder:', error);
    return NextResponse.json({ error: 'Failed to delete folder' }, { status: 500 });
  }
}

/**
 * Helper function to check if a folder is a descendant of another
 */
async function checkIfDescendant(ancestorId: number, descendantId: number): Promise<boolean> {
  const query = `
    WITH RECURSIVE folder_hierarchy AS (
      SELECT id, parent_id
      FROM leads.folders
      WHERE id = $1

      UNION ALL

      SELECT f.id, f.parent_id
      FROM leads.folders f
      INNER JOIN folder_hierarchy fh ON f.parent_id = fh.id
    )
    SELECT COUNT(*) as count
    FROM folder_hierarchy
    WHERE id = $2
  `;

  const result = await pool.query(query, [descendantId, ancestorId]);
  return parseInt(result.rows[0].count) > 0;
}
