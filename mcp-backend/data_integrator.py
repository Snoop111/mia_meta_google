import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
from abc import ABC, abstractmethod
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSourceConnector(ABC):
    """Abstract base class for data source connectors"""

    @abstractmethod
    async def fetch_data(self, start_date: str, end_date: str, **kwargs) -> pd.DataFrame:
        pass

    @abstractmethod
    def validate_credentials(self) -> bool:
        pass

class MetaAdsConnector(DataSourceConnector):
    """Meta Ads data connector"""

    def __init__(self, access_token: str, app_id: str, app_secret: str):
        self.access_token = access_token
        self.app_id = app_id
        self.app_secret = app_secret

    def validate_credentials(self) -> bool:
        try:
            # Add actual validation logic here
            return bool(self.access_token and self.app_id and self.app_secret)
        except Exception as e:
            logger.error(f"Meta Ads credential validation failed: {e}")
            return False

    async def fetch_data(self, start_date: str, end_date: str,
                        account_id: str = None, fields: List[str] = None) -> pd.DataFrame:
        """
        Fetch Meta Ads data

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            account_id: Meta Ads account ID
            fields: List of fields to fetch
        """
        try:
            from facebook_business.api import FacebookAdsApi
            from facebook_business.adobjects.adaccount import AdAccount
            from facebook_business.adobjects.adsinsights import AdsInsights

            # Initialize the API
            FacebookAdsApi.init(access_token=self.access_token)

            # Default fields if none provided
            if not fields:
                fields = [
                    AdsInsights.Field.date_start,
                    AdsInsights.Field.date_stop,
                    AdsInsights.Field.campaign_name,
                    AdsInsights.Field.adset_name,
                    AdsInsights.Field.ad_name,
                    AdsInsights.Field.impressions,
                    AdsInsights.Field.clicks,
                    AdsInsights.Field.spend,
                    AdsInsights.Field.reach,
                    AdsInsights.Field.frequency,
                    AdsInsights.Field.ctr,
                    AdsInsights.Field.cpc,
                    AdsInsights.Field.cpm,
                    AdsInsights.Field.actions,
                ]

            # Get account - if not provided, get all accessible accounts
            if not account_id:
                from facebook_business.adobjects.user import User
                me = User(fbid='me')
                accounts = me.get_ad_accounts()
                if not accounts:
                    logger.warning("No accessible ad accounts found")
                    return pd.DataFrame()
                account_id = accounts[0]['id']
                logger.info(f"Using account: {account_id}")

            # Ensure account_id has 'act_' prefix
            if not account_id.startswith('act_'):
                account_id = f'act_{account_id}'

            account = AdAccount(account_id)

            # Set up parameters for insights request
            params = {
                'time_range': {
                    'since': start_date,
                    'until': end_date
                },
                'level': AdsInsights.Level.ad,
                'breakdowns': [AdsInsights.Breakdowns.date],
            }

            # Fetch insights
            insights = account.get_insights(fields=fields, params=params)

            # Convert to DataFrame
            data_rows = []
            for insight in insights:
                row = {}
                for field in fields:
                    if field == AdsInsights.Field.actions:
                        # Handle actions field specially (conversions)
                        actions = insight.get('actions', [])
                        conversions = 0
                        for action in actions:
                            if action.get('action_type') in ['purchase', 'complete_registration', 'lead']:
                                conversions += int(action.get('value', 0))
                        row['conversions'] = conversions
                    else:
                        row[field] = insight.get(field, 0)

                # Add source identifier
                row['source'] = 'meta_ads'
                data_rows.append(row)

            if not data_rows:
                logger.warning("No data returned from Meta Ads API")
                return pd.DataFrame()

            df = pd.DataFrame(data_rows)

            # Clean up column names and data types
            if 'date_start' in df.columns:
                df['date'] = pd.to_datetime(df['date_start'])
                df = df.drop(['date_start', 'date_stop'], axis=1, errors='ignore')

            # Convert numeric columns
            numeric_cols = ['impressions', 'clicks', 'spend', 'reach', 'frequency', 'ctr', 'cpc', 'cpm', 'conversions']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            logger.info(f"Fetched {len(df)} rows from Meta Ads")
            return df

        except ImportError:
            logger.error("facebook-business package not installed. Run: pip install facebook-business")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching Meta Ads data: {e}")
            return pd.DataFrame()

class GoogleAdsConnector(DataSourceConnector):
    """Google Ads data connector"""

    def __init__(self, developer_token: str, client_id: str, client_secret: str, refresh_token: str):
        self.developer_token = developer_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

    def validate_credentials(self) -> bool:
        try:
            return bool(self.developer_token and self.client_id and
                       self.client_secret and self.refresh_token)
        except Exception as e:
            logger.error(f"Google Ads credential validation failed: {e}")
            return False

    async def fetch_data(self, start_date: str, end_date: str,
                        customer_id: str = None, query: str = None) -> pd.DataFrame:
        """
        Fetch Google Ads data

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            customer_id: Google Ads customer ID
            query: Custom GAQL query
        """
        try:
            from google.ads.googleads.client import GoogleAdsClient
            from google.ads.googleads.errors import GoogleAdsException

            # Create Google Ads client
            credentials = {
                "developer_token": self.developer_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "use_proto_plus": True
            }

            client = GoogleAdsClient.load_from_dict(credentials)

            # If no customer_id provided, get the first accessible customer
            if not customer_id:
                customer_service = client.get_service("CustomerService")
                accessible_customers = customer_service.list_accessible_customers()
                if not accessible_customers.resource_names:
                    logger.warning("No accessible customers found")
                    return pd.DataFrame()

                # Extract customer ID from resource name
                customer_id = accessible_customers.resource_names[0].split('/')[-1]
                logger.info(f"Using customer ID: {customer_id}")

            # Default GAQL query if none provided
            if not query:
                query = f"""
                SELECT
                  segments.date,
                  campaign.id,
                  campaign.name,
                  campaign.status,
                  metrics.impressions,
                  metrics.clicks,
                  metrics.cost_micros,
                  metrics.conversions,
                  metrics.ctr,
                  metrics.average_cpc
                FROM campaign
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY segments.date
                """

            # Execute the search request
            ga_service = client.get_service("GoogleAdsService")
            search_request = client.get_type("SearchGoogleAdsRequest")
            search_request.customer_id = customer_id
            search_request.query = query

            results = ga_service.search(request=search_request)

            # Convert results to DataFrame
            data_rows = []
            for row in results:
                data_row = {
                    'date': row.segments.date,
                    'campaign_id': str(row.campaign.id) if hasattr(row, 'campaign') else 'Unknown',
                    'campaign_name': row.campaign.name if hasattr(row, 'campaign') else 'Unknown',
                    'campaign_status': row.campaign.status.name if hasattr(row, 'campaign') and hasattr(row.campaign, 'status') else 'Unknown',
                    'impressions': row.metrics.impressions,
                    'clicks': row.metrics.clicks,
                    'cost_micros': row.metrics.cost_micros,
                    'conversions': row.metrics.conversions,
                    'ctr': row.metrics.ctr,
                    'average_cpc': row.metrics.average_cpc,
                    'source': 'google_ads'
                }
                data_rows.append(data_row)

            if not data_rows:
                logger.warning("No data returned from Google Ads API")
                return pd.DataFrame()

            df = pd.DataFrame(data_rows)

            # Convert data types
            df['date'] = pd.to_datetime(df['date'])
            df['spend'] = df['cost_micros'] / 1000000  # Convert micros to actual cost
            df = df.drop('cost_micros', axis=1)
            
            # Add missing columns expected by analytics modules
            if 'average_cpc' in df.columns:
                df['cpc'] = df['average_cpc'] / 1000000  # Convert from micros to actual cost
            
            # Calculate CPM if we have impressions and spend
            if 'impressions' in df.columns and 'spend' in df.columns:
                df['cpm'] = (df['spend'] / (df['impressions'] / 1000)).fillna(0)

            # Convert numeric columns
            numeric_cols = ['impressions', 'clicks', 'spend', 'conversions', 'ctr', 'average_cpc', 'cpc', 'cpm']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            logger.info(f"Fetched {len(df)} rows from Google Ads")
            return df

        except ImportError:
            logger.error("google-ads package not installed. Run: pip install google-ads")
            return pd.DataFrame()
        except GoogleAdsException as ex:
            logger.error(f"Google Ads API error: {ex}")
            for error in ex.failure.errors:
                logger.error(f"Error: {error.message}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching Google Ads data: {e}")
            return pd.DataFrame()

class GA4Connector(DataSourceConnector):
    """Google Analytics 4 data connector"""

    def __init__(self, credentials_path: str = None, property_id: str = None, 
                 oauth_credentials: dict = None):
        self.credentials_path = credentials_path
        self.property_id = property_id
        self.oauth_credentials = oauth_credentials
        self.use_oauth = oauth_credentials is not None

    def validate_credentials(self) -> bool:
        try:
            if self.use_oauth:
                # For OAuth, only validate that we have oauth credentials
                # property_id will be set at request time
                return bool(self.oauth_credentials)
            else:
                import os
                # For service account, we need both credentials file and property_id
                return os.path.exists(self.credentials_path) and bool(self.property_id)
        except Exception as e:
            logger.error(f"GA4 credential validation failed: {e}")
            return False

    async def fetch_data(self, start_date: str, end_date: str,
                        dimensions: List[str] = None, metrics: List[str] = None) -> pd.DataFrame:
        """
        Fetch GA4 data

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            dimensions: List of GA4 dimensions
            metrics: List of GA4 metrics
        """
        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.analytics.data_v1beta.types import (
                RunReportRequest,
                Dimension,
                Metric,
                DateRange,
            )
            from google.oauth2 import service_account
            from google.oauth2.credentials import Credentials

            # Load credentials - either from OAuth or service account
            if self.use_oauth:
                # Use OAuth credentials from user login
                credentials = Credentials(
                    token=self.oauth_credentials.get('token'),
                    refresh_token=self.oauth_credentials.get('refresh_token'),
                    token_uri=self.oauth_credentials.get('token_uri'),
                    client_id=self.oauth_credentials.get('client_id'),
                    client_secret=self.oauth_credentials.get('client_secret'),
                    scopes=['https://www.googleapis.com/auth/analytics.readonly']
                )
            else:
                # Use service account file (legacy approach)
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/analytics.readonly']
                )

            # Initialize the client
            client = BetaAnalyticsDataClient(credentials=credentials)

            # Default dimensions and metrics if none provided
            if not dimensions:
                dimensions = ['date', 'sessionDefaultChannelGrouping', 'sessionSourceMedium']
            if not metrics:
                metrics = ['sessions', 'newUsers', 'keyEvents', 'bounceRate', 'averageSessionDuration']

            # Create dimension and metric objects
            ga4_dimensions = [Dimension(name=dim) for dim in dimensions]
            ga4_metrics = [Metric(name=metric) for metric in metrics]

            # Create date range
            date_range = DateRange(start_date=start_date, end_date=end_date)

            # Create the request
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=ga4_dimensions,
                metrics=ga4_metrics,
                date_ranges=[date_range],
            )

            # Execute the request
            response = client.run_report(request=request)

            # Convert response to DataFrame
            data_rows = []
            for row in response.rows:
                data_row = {}

                # Add dimension values
                for i, dimension_value in enumerate(row.dimension_values):
                    dim_name = dimensions[i]
                    data_row[dim_name] = dimension_value.value

                # Add metric values
                for i, metric_value in enumerate(row.metric_values):
                    metric_name = metrics[i]
                    data_row[metric_name] = metric_value.value

                data_row['source'] = 'ga4'
                data_rows.append(data_row)

            if not data_rows:
                logger.warning("No data returned from GA4 API")
                return pd.DataFrame()

            df = pd.DataFrame(data_rows)

            # Convert date column to datetime
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')

            # Convert numeric columns
            numeric_cols = ['sessions', 'users', 'pageviews', 'bounceRate', 'avgSessionDuration']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # Rename columns for consistency
            column_mapping = {
                'sessionDefaultChannelGrouping': 'channel_grouping',
                'sessionSourceMedium': 'source_medium',
                'avgSessionDuration': 'avg_session_duration',
                'bounceRate': 'bounce_rate'
            }
            df = df.rename(columns=column_mapping)

            logger.info(f"Fetched {len(df)} rows from GA4")
            return df

        except ImportError:
            logger.error("google-analytics-data package not installed. Run: pip install google-analytics-data")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching GA4 data: {e}")
            return pd.DataFrame()

class DataIntegrator:
    """Main class for integrating data from multiple sources"""

    def __init__(self):
        self.connectors: Dict[str, DataSourceConnector] = {}

    def add_connector(self, name: str, connector: DataSourceConnector):
        """Add a data source connector"""
        if connector.validate_credentials():
            self.connectors[name] = connector
            logger.info(f"Added connector: {name}")
        else:
            logger.error(f"Failed to add connector {name}: Invalid credentials")

    def remove_connector(self, name: str):
        """Remove a data source connector"""
        if name in self.connectors:
            del self.connectors[name]
            logger.info(f"Removed connector: {name}")

    async def fetch_all_data(self, start_date: str, end_date: str,
                           connector_configs: Dict[str, Dict] = None) -> pd.DataFrame:
        """
        Fetch data from all configured connectors

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            connector_configs: Optional configurations for each connector
        """
        if not self.connectors:
            logger.warning("No connectors configured")
            return pd.DataFrame()

        # Prepare tasks for async execution
        tasks = []
        for name, connector in self.connectors.items():
            config = connector_configs.get(name, {}) if connector_configs else {}
            task = connector.fetch_data(start_date, end_date, **config)
            tasks.append((name, task))

        # Execute all tasks concurrently
        results = []
        for name, task in tasks:
            try:
                data = await task
                if not data.empty:
                    data['connector_name'] = name
                    results.append(data)
                    logger.info(f"Successfully fetched data from {name}")
                else:
                    logger.warning(f"No data returned from {name}")
            except Exception as e:
                logger.error(f"Failed to fetch data from {name}: {e}")

        # Combine all data
        if results:
            combined_df = pd.concat(results, ignore_index=True)
            logger.info(f"Combined data shape: {combined_df.shape}")
            return combined_df
        else:
            logger.warning("No data fetched from any connector")
            return pd.DataFrame()

    async def fetch_specific_data(self, connector_names: List[str], start_date: str,
                                end_date: str, connector_configs: Dict[str, Dict] = None) -> pd.DataFrame:
        """
        Fetch data from specific connectors only

        Args:
            connector_names: List of connector names to fetch data from
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            connector_configs: Optional configurations for each connector
        """
        # Filter connectors
        filtered_connectors = {name: self.connectors[name]
                             for name in connector_names
                             if name in self.connectors}

        if not filtered_connectors:
            logger.warning(f"No valid connectors found from: {connector_names}")
            return pd.DataFrame()

        # Temporarily store original connectors
        original_connectors = self.connectors.copy()
        self.connectors = filtered_connectors

        try:
            # Fetch data using existing method
            result = await self.fetch_all_data(start_date, end_date, connector_configs)
            return result
        finally:
            # Restore original connectors
            self.connectors = original_connectors

    def get_connector_status(self) -> Dict[str, bool]:
        """Get status of all connectors"""
        return {name: connector.validate_credentials()
                for name, connector in self.connectors.items()}

    def get_available_connectors(self) -> List[str]:
        """Get list of available connector names"""
        return list(self.connectors.keys())
