from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sha2, udf
from pyspark.sql.types import DecimalType, StringType
from pyspark.sql.utils import AnalysisException
from pyspark.sql import functions as F
from datetime import datetime
from pyspark.sql.window import Window


class AppConfigProcessor:
    def __init__(self,spark,app_config_path):
        self.spark = spark
        self.app_config_path = app_config_path
        self.appdf = spark.read.option("inferSchema", "true").json(app_config_path)
    
    def read_existing_table(self, store_path):
        try:
            existing_df = self.spark.read.parquet(store_path)
            return existing_df
        except AnalysisException as e:
            print(f"The Parquet file at {store_path} does not exist.")
            return None
    
    
    def lookup_table(self, df, loc):
        current_date = datetime.now().strftime("%Y-%m-%d")

        df = df.withColumn("start_date", F.lit(current_date)) \
               .withColumn("end_date", F.lit("0000-00-00")).withColumn("is_current", F.lit(False))

        df = df.select(col("advertising_id"),
                       col("user_id"),
                       col("masked_advertising_id"),
                       col("masked_user_id"),
                       col("start_date"),
                       col("end_date"),
                       col("is_current"))

        existing_df = self.read_existing_table(loc)

        if existing_df is not None:
            df = existing_df.unionAll(df)

        window_spec = Window.partitionBy("advertising_id").orderBy("start_date")

        df = df.withColumn("is_current",F.when(F.col("user_id") != F.lead("user_id").over(window_spec), False).otherwise(True)).withColumn("end_date",F.when(F.col("user_id") != F.lead("user_id").over(window_spec), current_date).otherwise(F.col("end_date")))

        return df

    
    
    def process_section(self, section):
        print(f"Processing '{section}' section...")
        sor_col = col(section)
        sor_df = self.appdf.select(sor_col)
        source_dict = sor_df.first().asDict()
        source_df = source_dict[section]
        #print(source_df)

        source_sou = source_df['source_bucket']
        source_dest = source_df['destination_bucket']
        source_tran = source_df['transformations']  

        #print(source_tran['to_string']['location'])
        return source_sou, source_dest, source_tran



    def apply_transformations(self, df, transformations):
        print("Applying transformations...")
        column_to_join=transformations['to_string']['location']
        column_to_mask=transformations['to_string']['mask']
        column_to_dec_lat=transformations['to_decimal']['latitude']
        column_to_dec_lon=transformations['to_decimal']['longitude']

        #print(column_to_mask)
        join_list_udf = udf(lambda lst: ",".join(lst) if lst else "", StringType())
        masked_df = df.withColumn(column_to_join,join_list_udf(df[column_to_join]))

        if isinstance(column_to_mask, list):
            for i in column_to_mask:
                masked_df = masked_df.withColumn("masked_"+i, sha2(col(i), 256).cast("string"))
        else:
            masked_df = masked_df.withColumn("masked_"+column_to_mask, sha2(col(column_to_mask), 256).cast("string"))
        masked_df = masked_df.withColumn(column_to_dec_lat, col(column_to_dec_lat).cast(DecimalType(10, 7)))
        masked_df = masked_df.withColumn(column_to_dec_lon, col(column_to_dec_lon).cast(DecimalType(10, 7)))

        #print(masked_df.head())
        return masked_df




    def process_and_write(self, section):
        
        source_sou, source_dest, source_tran = self.process_section(section)
        print(f"Source: {source_sou}, Destination: {source_dest}")
    
        df = self.spark.read.parquet(source_sou)
        
        return df,source_dest,source_tran
        


def main():
    app_config_path = "s3://shriraaman.s-landingbucket-01/source/app-config.json"
    delta_loc="s3://shriraaman.s-landingbucket-01/source/lookup/"

    # Create a Spark session
    spark = SparkSession.builder.master("yarn").appName("SparkSQLDemoa").config("spark.jars.packages", "io.delta:delta-core_2.12:1.0.0").config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension").config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog").getOrCreate()
    
    app_processor = None  # Initialize to None

    try:
        app_processor = AppConfigProcessor(spark, app_config_path)
        
        df_a,active_des,active_tran=app_processor.process_and_write('actives')
        df_v,view_des,view_tran=app_processor.process_and_write('viewership')
        
        masked_df_a = app_processor.apply_transformations(df_a, active_tran)
        masked_df_v = app_processor.apply_transformations(df_v, view_tran)
        #masked_df_v.show(5)
        masked_df_v.write.partitionBy("month","date").mode("overwrite").parquet(view_des)
        masked_df_a.write.partitionBy("month","date").mode("overwrite").parquet(active_des)
        
        df=app_processor.lookup_table(masked_df_a,delta_loc)
        df = df.repartition(1)
        df.write.format("delta").mode("append").save(delta_loc)
                
    finally:
        spark.stop()
    
    
    
if __name__ == "__main__":
    main()






