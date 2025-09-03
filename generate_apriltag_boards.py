#!/usr/bin/env python3
"""
Generate AprilTag calibration boards for multi-camera calibration.

This script generates high-resolution AprilTag boards with the following specifications:
- AprilTag family: 36h11 (ID 20 in OpenCV)
- Grid layout: 7x7 tags per board
- Tag size: 40mm (0.04m)
- Spacing between tags: 10mm (0.01m)
- Three boards with ID ranges: [0-48], [49-97], [98-146]
"""

import os
import sys
import numpy as np
import cv2
from pathlib import Path
from typing import List, Tuple
import argparse

# Try to import optional dependencies
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    HAS_MATPLOTLIB = True
except ImportError:
    print("Warning: matplotlib not installed. PDF generation will be skipped.")
    print("Install with: pip install matplotlib")
    HAS_MATPLOTLIB = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    print("Warning: PyYAML not installed. YAML configuration will not be available.")
    print("Install with: pip install pyyaml")
    HAS_YAML = False


def load_config(config_path: str = "config.yaml") -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Configuration dictionary with default values if file not found
    """
    default_config = {
        'apriltag': {
            'family': '36h11',
            'grid_x': 7,
            'grid_y': 7,
            'tag_size_mm': 40,
            'spacing_mm': 10,
            'border_mm': 10,
            'dpi': 300
        },
        'boards': [
            {'name': 'Board 1', 'start_id': 0, 'end_id': 48},
            {'name': 'Board 2', 'start_id': 49, 'end_id': 97},
            {'name': 'Board 3', 'start_id': 98, 'end_id': 146}
        ],
        'output': {
            'directory': 'apriltag_boards'
        },
        'features': {
            'corner_markers': True,
            'corner_marker_size_mm': 5,
            'corner_marker_thickness_mm': 1,
            'black_corner_squares': True,
            'corner_square_size_mm': 10
        }
    }
    
    if not HAS_YAML:
        print(f"Warning: PyYAML not available, using default configuration")
        return default_config
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Merge with defaults for missing keys
        for key in default_config:
            if key not in config:
                config[key] = default_config[key]
            elif isinstance(default_config[key], dict):
                for subkey in default_config[key]:
                    if subkey not in config[key]:
                        config[key][subkey] = default_config[key][subkey]
        
        print(f"Loaded configuration from: {config_path}")
        return config
        
    except FileNotFoundError:
        print(f"Warning: Config file '{config_path}' not found, using defaults")
        return default_config
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file '{config_path}': {e}")
        print("Using default configuration")
        return default_config


def get_apriltag_family_id(family_name: str) -> int:
    """
    Convert AprilTag family name to OpenCV constant.
    
    Args:
        family_name: Family name like '36h11', '25h9', etc.
        
    Returns:
        OpenCV ArUco dictionary constant
    """
    family_map = {
        '36h11': cv2.aruco.DICT_APRILTAG_36h11,
        '25h9': cv2.aruco.DICT_APRILTAG_25h9,
        '16h5': cv2.aruco.DICT_APRILTAG_16h5
    }
    
    if family_name not in family_map:
        print(f"Warning: Unknown AprilTag family '{family_name}', using 36h11")
        return cv2.aruco.DICT_APRILTAG_36h11
    
    return family_map[family_name]

class AprilTagBoardGenerator:
    """Generate AprilTag calibration boards for printing."""
    
    def __init__(self, 
                 family: int = cv2.aruco.DICT_APRILTAG_36h11,
                 grid_x: int = 7,
                 grid_y: int = 7,
                 tag_size_mm: float = 40,
                 spacing_mm: float = 10,
                 border_mm: float = 10,
                 dpi: int = 300):
        """
        Initialize the AprilTag board generator.
        
        Args:
            family: AprilTag dictionary family (default: 36h11)
            grid_x: Number of tags in X direction
            grid_y: Number of tags in Y direction
            tag_size_mm: Size of each tag in millimeters
            spacing_mm: Spacing between tags in millimeters
            border_mm: Border around the entire board in millimeters
            dpi: Dots per inch for image generation
        """
        self.family = family
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.tag_size_mm = tag_size_mm
        self.spacing_mm = spacing_mm
        self.border_mm = border_mm
        self.dpi = dpi
        
        # Calculate pixels per mm
        self.pixels_per_mm = self.dpi / 25.4
        
        # Calculate sizes in pixels
        self.tag_size_px = int(self.tag_size_mm * self.pixels_per_mm)
        self.spacing_px = int(self.spacing_mm * self.pixels_per_mm)
        self.border_px = int(self.border_mm * self.pixels_per_mm)
        
        # Calculate total board size
        self.board_width_mm = (self.grid_x * self.tag_size_mm + 
                               (self.grid_x - 1) * self.spacing_mm + 
                               2 * self.border_mm)
        self.board_height_mm = (self.grid_y * self.tag_size_mm + 
                                (self.grid_y - 1) * self.spacing_mm + 
                                2 * self.border_mm)
        
        self.board_width_px = int(self.board_width_mm * self.pixels_per_mm)
        self.board_height_px = int(self.board_height_mm * self.pixels_per_mm)
        
        # Load AprilTag dictionary
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(self.family)
        
        print(f"Initialized AprilTag Board Generator:")
        print(f"  - Family: 36h11 (ID {self.family})")
        print(f"  - Grid: {self.grid_x}x{self.grid_y}")
        print(f"  - Tag size: {self.tag_size_mm}mm ({self.tag_size_px}px)")
        print(f"  - Spacing: {self.spacing_mm}mm ({self.spacing_px}px)")
        print(f"  - Border: {self.border_mm}mm ({self.border_px}px)")
        print(f"  - Board size: {self.board_width_mm:.1f}x{self.board_height_mm:.1f}mm")
        print(f"  - Resolution: {self.dpi} DPI")
    
    def generate_board(self, 
                      board_id: int, 
                      start_id: int, 
                      end_id: int) -> np.ndarray:
        """
        Generate a single AprilTag board.
        
        Args:
            board_id: Board number (1, 2, 3, etc.)
            start_id: Starting tag ID (inclusive)
            end_id: Ending tag ID (inclusive)
        
        Returns:
            Board image as numpy array
        """
        # Create white background
        board = np.ones((self.board_height_px, self.board_width_px), dtype=np.uint8) * 255
        
        # Calculate starting position for tags (centered on the board)
        start_x = self.border_px
        start_y = self.border_px
        
        # Generate and place tags
        current_id = start_id
        for row in range(self.grid_y):
            for col in range(self.grid_x):
                if current_id > end_id:
                    break
                
                # Generate AprilTag marker
                marker_img = cv2.aruco.generateImageMarker(
                    self.aruco_dict, 
                    current_id, 
                    self.tag_size_px
                )
                
                # Calculate position
                x = start_x + col * (self.tag_size_px + self.spacing_px)
                y = start_y + row * (self.tag_size_px + self.spacing_px)
                
                # Place marker on board
                board[y:y+self.tag_size_px, x:x+self.tag_size_px] = marker_img
                
                current_id += 1
        
        # Add black squares (10mm) at the intersections between AprilTags
        # These squares are placed in the gaps between tags, with corners touching the adjacent tag corners
        corner_square_size = int(10 * self.pixels_per_mm)  # 10mm squares
        
        # Place black squares at ALL intersections including edges
        # Edge squares are full 10mm squares with half extending outside the visible area
        for row in range(self.grid_y + 1):  # Include top and bottom edges
            for col in range(self.grid_x + 1):  # Include left and right edges
                # Calculate the position of the black square
                # All squares are 10mm, but edge squares are centered on the edge
                if row == 0:
                    # Top edge - square flush with top edge
                    square_y = 0
                elif row == self.grid_y:
                    # Bottom edge - square flush with bottom edge
                    square_y = self.board_height_px - corner_square_size
                else:
                    # Interior - square in the gap between tags
                    square_y = start_y + row * self.tag_size_px + (row - 1) * self.spacing_px
                
                if col == 0:
                    # Left edge - square flush with left edge
                    square_x = 0
                elif col == self.grid_x:
                    # Right edge - square flush with right edge
                    square_x = self.board_width_px - corner_square_size
                else:
                    # Interior - square in the gap between tags
                    square_x = start_x + col * self.tag_size_px + (col - 1) * self.spacing_px
                
                # Clip to image boundaries
                clip_x_start = max(0, square_x)
                clip_y_start = max(0, square_y)
                clip_x_end = min(self.board_width_px, square_x + corner_square_size)
                clip_y_end = min(self.board_height_px, square_y + corner_square_size)
                
                # Place the black square (only the visible part)
                if clip_x_start < clip_x_end and clip_y_start < clip_y_end:
                    board[clip_y_start:clip_y_end, clip_x_start:clip_x_end] = 0
        
        # Add corner markers for alignment
        marker_size = int(5 * self.pixels_per_mm)
        marker_thickness = int(1 * self.pixels_per_mm)
        
        # Top-left corner
        cv2.line(board, (5, 5), (5 + marker_size, 5), 0, marker_thickness)
        cv2.line(board, (5, 5), (5, 5 + marker_size), 0, marker_thickness)
        
        # Top-right corner
        cv2.line(board, (self.board_width_px - 5, 5), 
                (self.board_width_px - 5 - marker_size, 5), 0, marker_thickness)
        cv2.line(board, (self.board_width_px - 5, 5), 
                (self.board_width_px - 5, 5 + marker_size), 0, marker_thickness)
        
        # Bottom-left corner
        cv2.line(board, (5, self.board_height_px - 5), 
                (5 + marker_size, self.board_height_px - 5), 0, marker_thickness)
        cv2.line(board, (5, self.board_height_px - 5), 
                (5, self.board_height_px - 5 - marker_size), 0, marker_thickness)
        
        # Bottom-right corner
        cv2.line(board, (self.board_width_px - 5, self.board_height_px - 5), 
                (self.board_width_px - 5 - marker_size, self.board_height_px - 5), 0, marker_thickness)
        cv2.line(board, (self.board_width_px - 5, self.board_height_px - 5), 
                (self.board_width_px - 5, self.board_height_px - 5 - marker_size), 0, marker_thickness)
        
        return board
    
    def save_board_image(self, board: np.ndarray, output_path: str):
        """Save board as PNG image."""
        # Add DPI information to the image metadata
        cv2.imwrite(output_path, board)
        print(f"  Saved: {output_path}")
    
    def save_board_pdf(self, board: np.ndarray, output_path: str, board_id: int, 
                      start_id: int, end_id: int):
        """Save board as PDF for printing."""
        if not HAS_MATPLOTLIB:
            print(f"  Skipping PDF generation (matplotlib not installed)")
            return
        
        # Create figure with correct size in inches
        fig_width = self.board_width_mm / 25.4
        fig_height = self.board_height_mm / 25.4
        
        fig = plt.figure(figsize=(fig_width, fig_height))
        ax = fig.add_subplot(111)
        
        # Display image
        ax.imshow(board, cmap='gray', vmin=0, vmax=255)
        ax.axis('off')
        
        # Remove margins
        plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
        plt.margins(0, 0)
        
        # Save as PDF
        with PdfPages(output_path) as pdf:
            pdf.savefig(fig, bbox_inches='tight', pad_inches=0, dpi=self.dpi)
            
            # Add metadata
            d = pdf.infodict()
            d['Title'] = f'AprilTag Board {board_id}'
            d['Subject'] = f'Calibration board with AprilTag IDs {start_id}-{end_id}'
            d['Keywords'] = f'AprilTag, Calibration, 36h11, {self.grid_x}x{self.grid_y}'
            d['Producer'] = 'AprilTag Board Generator'
        
        plt.close(fig)
        print(f"  Saved: {output_path}")
    
    def generate_all_boards(self, output_dir: str, board_configs: List[Tuple[int, int]]):
        """
        Generate all calibration boards.
        
        Args:
            output_dir: Output directory path
            board_configs: List of (start_id, end_id) tuples for each board
        """
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\nGenerating {len(board_configs)} AprilTag boards...")
        
        boards = []
        for board_num, (start_id, end_id) in enumerate(board_configs, 1):
            print(f"\nGenerating Board {board_num} (IDs {start_id}-{end_id})...")
            
            # Generate board
            board = self.generate_board(board_num, start_id, end_id)
            boards.append(board)
            
            # Save as PNG
            png_path = output_path / f"board_{board_num}_ids_{start_id}-{end_id}.png"
            self.save_board_image(board, str(png_path))
            
            # Save as PDF
            pdf_path = output_path / f"board_{board_num}_ids_{start_id}-{end_id}.pdf"
            self.save_board_pdf(board, str(pdf_path), board_num, start_id, end_id)
        
        # Generate specifications document
        self.save_specifications(output_path, board_configs)
        
        return boards
    
    def save_specifications(self, output_dir: Path, board_configs: List[Tuple[int, int]]):
        """Save board specifications to a text file."""
        specs_path = output_dir / "board_specifications.txt"
        
        with open(specs_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("APRILTAG CALIBRATION BOARD SPECIFICATIONS\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("GENERAL SPECIFICATIONS:\n")
            f.write("-" * 30 + "\n")
            f.write(f"AprilTag Family: 36h11 (OpenCV ID: {self.family})\n")
            f.write(f"Grid Layout: {self.grid_x} x {self.grid_y} tags\n")
            f.write(f"Tag Size: {self.tag_size_mm}mm x {self.tag_size_mm}mm\n")
            f.write(f"Tag Spacing: {self.spacing_mm}mm (edge to edge)\n")
            f.write(f"Board Border: {self.border_mm}mm\n")
            f.write(f"Total Board Size: {self.board_width_mm:.1f}mm x {self.board_height_mm:.1f}mm\n")
            f.write(f"Image Resolution: {self.dpi} DPI\n")
            f.write(f"Image Size: {self.board_width_px} x {self.board_height_px} pixels\n")
            f.write("\n")
            
            f.write("BOARD CONFIGURATIONS:\n")
            f.write("-" * 30 + "\n")
            for board_num, (start_id, end_id) in enumerate(board_configs, 1):
                num_tags = end_id - start_id + 1
                f.write(f"Board {board_num}:\n")
                f.write(f"  - AprilTag ID Range: {start_id} to {end_id}\n")
                f.write(f"  - Number of Tags: {num_tags}\n")
                f.write(f"  - File Names:\n")
                f.write(f"    * PNG: board_{board_num}_ids_{start_id}-{end_id}.png\n")
                f.write(f"    * PDF: board_{board_num}_ids_{start_id}-{end_id}.pdf\n")
                f.write("\n")
            
            f.write("PRINTING INSTRUCTIONS:\n")
            f.write("-" * 30 + "\n")
            f.write("1. Print the PDF files at 100% scale (no scaling/fit to page)\n")
            f.write("2. Verify the printed size using the 100mm ruler at the bottom\n")
            f.write("3. Mount the printed boards on rigid, flat surfaces\n")
            f.write("4. Ensure boards are clean and free from reflections\n")
            f.write("5. Use corner markers for precise alignment if needed\n")
            f.write("\n")
            
            f.write("CALIBRATION CONFIGURATION:\n")
            f.write("-" * 30 + "\n")
            f.write("Add the following to your calibration YAML file:\n\n")
            f.write("board_type: 2  # AprilTag board\n")
            f.write("apriltag_family: 20  # 36h11\n")
            f.write(f"apriltag_grid_x: {self.grid_x}\n")
            f.write(f"apriltag_grid_y: {self.grid_y}\n")
            f.write(f"apriltag_size: {self.tag_size_mm / 1000:.3f}  # in meters\n")
            f.write(f"apriltag_spacing: {self.spacing_mm / 1000:.3f}  # in meters\n")
            f.write("apriltag_board_id_ranges:\n")
            for start_id, end_id in board_configs:
                f.write(f"  - [{start_id}, {end_id}]\n")
            f.write("\n")
            
            f.write("USAGE NOTES:\n")
            f.write("-" * 30 + "\n")
            f.write("- Each board can be used independently or together\n")
            f.write("- Ensure adequate lighting for tag detection\n")
            f.write("- Maintain a reasonable distance for camera resolution\n")
            f.write("- Tags should occupy at least 5x5 pixels in the image\n")
            f.write("\n")
            
            f.write("=" * 60 + "\n")
            f.write("Generated by generate_apriltag_boards.py\n")
            f.write("=" * 60 + "\n")
        
        print(f"\nSaved specifications: {specs_path}")


def main():
    """Main function to generate AprilTag boards."""
    parser = argparse.ArgumentParser(
        description="Generate AprilTag calibration boards for multi-camera calibration"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="YAML configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output directory for generated boards (overrides config)"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        help="DPI resolution for generated images (overrides config)"
    )
    parser.add_argument(
        "--grid-x",
        type=int,
        help="Number of tags in X direction (overrides config)"
    )
    parser.add_argument(
        "--grid-y",
        type=int,
        help="Number of tags in Y direction (overrides config)"
    )
    parser.add_argument(
        "--tag-size",
        type=float,
        help="Tag size in millimeters (overrides config)"
    )
    parser.add_argument(
        "--spacing",
        type=float,
        help="Spacing between tags in millimeters (overrides config)"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command-line arguments if provided
    apriltag_config = config['apriltag'].copy()
    if args.dpi is not None:
        apriltag_config['dpi'] = args.dpi
    if args.grid_x is not None:
        apriltag_config['grid_x'] = args.grid_x
    if args.grid_y is not None:
        apriltag_config['grid_y'] = args.grid_y
    if args.tag_size is not None:
        apriltag_config['tag_size_mm'] = args.tag_size
    if args.spacing is not None:
        apriltag_config['spacing_mm'] = args.spacing
    
    # Override output directory if specified
    output_dir = args.output if args.output else config['output']['directory']
    
    # Convert board configs to tuples for compatibility
    board_configs = [(board['start_id'], board['end_id']) for board in config['boards']]
    
    # Get AprilTag family ID
    family_id = get_apriltag_family_id(apriltag_config['family'])
    
    # Create generator with merged configuration
    generator = AprilTagBoardGenerator(
        family=family_id,
        grid_x=apriltag_config['grid_x'],
        grid_y=apriltag_config['grid_y'],
        tag_size_mm=apriltag_config['tag_size_mm'],
        spacing_mm=apriltag_config['spacing_mm'],
        border_mm=apriltag_config['border_mm'],
        dpi=apriltag_config['dpi']
    )
    
    # Generate all boards
    boards = generator.generate_all_boards(output_dir, board_configs)
    
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE!")
    print("=" * 60)
    print(f"\nGenerated {len(boards)} AprilTag calibration boards")
    print(f"Output directory: {output_dir}/")
    print("\nNext steps:")
    print("1. Review the generated boards visually")
    print("2. Print the PDF files at 100% scale")
    print("3. Verify dimensions using the printed ruler")
    print("4. Mount on rigid surfaces for calibration")
    print("\nRefer to 'board_specifications.txt' for detailed information")


if __name__ == "__main__":
    main()