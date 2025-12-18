import io
import numpy as np
import matplotlib
matplotlib.use('Agg') # Crucial for server environment
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.img_tiles as cimgt

def generate_heatmap(lats, lons, data, bounds, title_main, title_sub):
    """
    Generates a PNG byte stream from raw numpy arrays.
    """
    # 1. Mask Low Precipitation (Transparency)
    data_masked = np.where(data < 0.1, np.nan, data)

    # 2. Setup Figure
    fig = plt.figure(figsize=(12, 10))
    
    tiler = cimgt.GoogleTiles(style='satellite')
    ax = plt.axes(projection=tiler.crs)
    ax.set_extent([bounds['left'], bounds['right'], bounds['bottom'], bounds['top']], crs=ccrs.PlateCarree())

    # 3. Background
    try:
        ax.add_image(tiler, 8) 
    except Exception:
        ax.coastlines(color='white')
        ax.stock_img()

    # 4. Plot Heatmap
    mesh = ax.pcolormesh(
        lons, lats, data_masked, 
        transform=ccrs.PlateCarree(), 
        cmap='jet', 
        vmin=0.1, vmax=15.0, alpha=0.6
    )
    
    # 5. Decorators
    cbar = plt.colorbar(mesh, ax=ax, orientation='horizontal', pad=0.03, fraction=0.04)
    cbar.set_label('Precipitation (mm/hr)', size=10)
    cbar.ax.tick_params(labelsize=9)
    
    gl = ax.gridlines(draw_labels=True, linestyle='--', alpha=0.3, color='white')
    gl.top_labels = False
    gl.right_labels = False

    # Titles
    full_title = f"{title_main}\n{title_sub}"
    ax.set_title(full_title, fontsize=14, fontweight='bold', pad=12, color='black')

    # 6. Save
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()