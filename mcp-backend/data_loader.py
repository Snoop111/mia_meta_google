"""
Data Loading Module - API Only
Handles CSV data loading from uploaded files
"""

import pandas as pd
import io
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DataLoader:
    """Handles loading data from uploaded files"""
    
    @staticmethod
    def load_csv_from_bytes(file_bytes: bytes, filename: str) -> Optional[pd.DataFrame]:
        """Load CSV from bytes (for uploaded files)"""
        encodings = ['utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                content_str = file_bytes.decode(encoding)
                
                # Handle different CSV formats
                logger.info(f"Determining parser for {filename}")
                logger.info(f"Content preview: {content_str[:200]}")
                
                if ('google' in filename.lower() or 
                    'ads performance' in filename.lower() or 
                    'ads performance' in content_str[:500] or
                    any(indicator in content_str[:1000] for indicator in ['Campaign,Ad group', 'Clicks,Impr.,CTR', 'Cost,Conversions'])):
                    logger.info(f"Using Google Ads parser for {filename}")
                    df = DataLoader._parse_google_ads_csv(content_str, filename)
                elif 'ga4' in filename.lower() or content_str.startswith('#'):
                    logger.info(f"Using GA4 parser for {filename}")
                    df = DataLoader._parse_ga4_csv(content_str, filename)
                elif ('ad group report' in content_str.lower()[:200] or 
                      'meta' in filename.lower() or
                      'ad group' in content_str.lower()[:500] or
                      'ad group report' in filename.lower() or
                      any(indicator in content_str[:1000] for indicator in ['Ad group status', 'Ad group\tCampaign', 'Impr.\tInteractions', 'All time'])):
                    logger.info(f"Using Meta parser for {filename}")
                    df = DataLoader._parse_meta_csv(content_str, filename)
                else:
                    logger.info(f"Using generic parser for {filename}")
                    df = DataLoader._parse_generic_csv(content_str, filename)
                    
                if df is not None and not df.empty:
                    logger.info(f"Successfully loaded {filename} with {encoding} encoding")
                    return df
                    
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading {filename}: {e}")
                return None
        
        logger.error(f"Could not read {filename} with any encoding")
        return None
    
    @staticmethod
    def _parse_generic_csv(content_str: str, filename: str) -> Optional[pd.DataFrame]:
        """Parse generic CSV with robust error handling"""
        try:
            # Try multiple parsing strategies
            strategies = [
                # Standard parsing
                lambda: pd.read_csv(io.StringIO(content_str)),
                # Skip bad lines
                lambda: pd.read_csv(io.StringIO(content_str), on_bad_lines='skip'),
                # Use different separator
                lambda: pd.read_csv(io.StringIO(content_str), sep=';'),
                # Skip initial rows that might be metadata
                lambda: pd.read_csv(io.StringIO(content_str), skiprows=1),
                lambda: pd.read_csv(io.StringIO(content_str), skiprows=2),
                # Flexible quoting
                lambda: pd.read_csv(io.StringIO(content_str), quoting=1),  # QUOTE_ALL
                # Error handling with skip
                lambda: pd.read_csv(io.StringIO(content_str), error_bad_lines=False, warn_bad_lines=False),
            ]
            
            for i, strategy in enumerate(strategies):
                try:
                    df = strategy()
                    if df is not None and not df.empty and len(df.columns) > 1:
                        logger.info(f"Successfully parsed {filename} using strategy {i+1}")
                        return df
                except Exception as e:
                    logger.debug(f"Strategy {i+1} failed for {filename}: {e}")
                    continue
            
            # If all strategies fail, try to find a working subset
            lines = content_str.strip().split('\n')
            if len(lines) > 5:
                # Try parsing from different starting points
                for start_line in range(min(5, len(lines) - 2)):
                    try:
                        subset_content = '\n'.join(lines[start_line:])
                        df = pd.read_csv(io.StringIO(subset_content), on_bad_lines='skip')
                        if df is not None and not df.empty and len(df.columns) > 1:
                            logger.info(f"Successfully parsed {filename} starting from line {start_line + 1}")
                            return df
                    except Exception:
                        continue
            
            logger.warning(f"Could not parse {filename} with any strategy")
            return None
            
        except Exception as e:
            logger.error(f"Error in generic CSV parsing for {filename}: {e}")
            return None
    
    @staticmethod
    def _parse_google_ads_csv(content_str: str, filename: str) -> Optional[pd.DataFrame]:
        """Parse Google Ads CSV that has title rows before actual data"""
        try:
            lines = content_str.strip().split('\n')
            
            # Find the line with actual column headers (has common Google Ads columns)
            header_indicators = ['Campaign', 'Ad group', 'Clicks', 'Impr.', 'Cost', 'Conversions']
            header_line_idx = None
            
            for i, line in enumerate(lines):
                # Count how many indicators are in this line
                indicators_found = sum(1 for indicator in header_indicators if indicator in line)
                
                if indicators_found >= 3:
                    header_line_idx = i
                    break
            
            if header_line_idx is None:
                logger.warning(f"Could not find header row in {filename}, trying default parsing")
                return pd.read_csv(io.StringIO(content_str))
            
            # Create CSV content starting from the header line
            csv_content = '\n'.join(lines[header_line_idx:])
            df = pd.read_csv(io.StringIO(csv_content))
            
            logger.info(f"Google Ads CSV parsed successfully: {df.shape[0]} rows, {df.shape[1]} columns")
            
            return df
            
        except Exception as e:
            logger.error(f"Error parsing Google Ads CSV {filename}: {e}")
            return None
    
    @staticmethod
    def _parse_ga4_csv(content_str: str, filename: str) -> Optional[pd.DataFrame]:
        """Parse GA4 CSV that has # comment headers"""
        try:
            lines = content_str.strip().split('\n')
            
            # Find the first line that doesn't start with # and has data
            data_start_idx = None
            for i, line in enumerate(lines):
                if not line.startswith('#') and ',' in line and not line.strip() == '':
                    data_start_idx = i
                    break
            
            if data_start_idx is None:
                logger.warning(f"Could not find data start in GA4 file {filename}")
                return None
            
            # Create CSV content starting from the data line, but handle inconsistent fields
            csv_content = '\n'.join(lines[data_start_idx:])
            
            # Try multiple strategies for parsing corrupted CSV
            strategies = [
                # Standard parsing
                lambda: pd.read_csv(io.StringIO(csv_content)),
                # Skip bad lines
                lambda: pd.read_csv(io.StringIO(csv_content), on_bad_lines='skip'),
                # Use error handling
                lambda: pd.read_csv(io.StringIO(csv_content), error_bad_lines=False),
                # Parse only clean lines manually
                lambda: DataLoader._parse_clean_lines_only(csv_content)
            ]
            
            for i, strategy in enumerate(strategies):
                try:
                    df = strategy()
                    if df is not None and not df.empty:
                        logger.info(f"GA4 CSV parsed successfully with strategy {i+1}: {df.shape[0]} rows, {df.shape[1]} columns")
                        logger.info(f"GA4 columns: {list(df.columns)}")
                        return df
                except Exception as e:
                    logger.debug(f"GA4 parsing strategy {i+1} failed: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing GA4 CSV {filename}: {e}")
            return None
    
    @staticmethod
    def _parse_clean_lines_only(csv_content: str) -> Optional[pd.DataFrame]:
        """Parse only lines that have consistent field count"""
        lines = csv_content.strip().split('\n')
        if len(lines) < 2:
            return None
            
        # Get header line
        header = lines[0]
        expected_fields = len(header.split(','))
        
        # Filter lines that have the expected field count
        clean_lines = [header]
        for line in lines[1:]:
            if len(line.split(',')) == expected_fields:
                clean_lines.append(line)
        
        if len(clean_lines) < 2:  # Need at least header + 1 data row
            return None
            
        clean_content = '\n'.join(clean_lines)
        return pd.read_csv(io.StringIO(clean_content))
    
    @staticmethod
    def _parse_meta_csv(content_str: str, filename: str) -> Optional[pd.DataFrame]:
        """Parse Meta Ads CSV that has title rows before headers"""
        try:
            logger.info(f"Attempting Meta CSV parsing for {filename}")
            lines = content_str.strip().split('\n')
            
            # Find the line with actual column headers (has common Meta columns)
            header_indicators = ['Ad group', 'Campaign', 'Impr.', 'Cost', 'Conversions', 'Interactions']
            header_line_idx = None
            
            for i, line in enumerate(lines):
                # Count how many indicators are in this line
                indicators_found = sum(1 for indicator in header_indicators if indicator in line)
                logger.info(f"Line {i}: {indicators_found} indicators in: {line[:100]}...")
                
                if indicators_found >= 3:
                    header_line_idx = i
                    logger.info(f"Selected line {i} as Meta header row")
                    break
            
            if header_line_idx is None:
                logger.warning(f"Could not find header row in Meta file {filename}")
                return None
            
            # Get data lines, excluding "Total:" summary rows
            data_lines = []
            for line in lines[header_line_idx:]:
                if not line.startswith('Total:') and line.strip():
                    data_lines.append(line)
            
            if len(data_lines) < 2:  # Need header + at least 1 data row
                logger.warning(f"Not enough data lines in Meta file {filename}")
                return None
            
            # Create CSV content and try different separators
            csv_content = '\n'.join(data_lines)
            
            # Try different separators (tabs are common in Meta exports)
            separators = ['\t', ',', ';']
            df = None
            
            for sep in separators:
                try:
                    temp_df = pd.read_csv(io.StringIO(csv_content), sep=sep, on_bad_lines='skip')
                    # Check if we got meaningful columns (more than 2 and not all "Unnamed")
                    if (temp_df.shape[1] > 2 and 
                        not all(col.startswith('Unnamed') for col in temp_df.columns)):
                        df = temp_df
                        logger.info(f"Meta CSV parsed with separator '{sep}'")
                        break
                except Exception as e:
                    logger.debug(f"Meta parsing failed with separator '{sep}': {e}")
                    continue
            
            if df is None:
                # Fallback to comma separator
                df = pd.read_csv(io.StringIO(csv_content), on_bad_lines='skip')
            
            logger.info(f"Meta CSV parsed successfully: {df.shape[0]} rows, {df.shape[1]} columns")
            logger.info(f"Meta columns: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error parsing Meta CSV {filename}: {e}")
            return None
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame, required_columns: list = None) -> bool:
        """Validate that dataframe has required structure"""
        if df is None or df.empty:
            return False
        
        if required_columns:
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.warning(f"Missing columns: {missing_columns}")
        
        return True