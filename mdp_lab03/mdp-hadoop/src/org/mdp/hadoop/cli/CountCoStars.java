package org.mdp.hadoop.cli;

import java.io.IOException;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.util.GenericOptionsParser;

/**
 * Counts the number of movies in which each pair of stars appeared together.
 *
 * Input and output records have the form:
 * starA##starB[tab]count
 */
public class CountCoStars {

	public static class CountCoStarsMapper
			extends Mapper<Object, Text, Text, IntWritable> {

		@Override
		public void map(Object keyIn, Text valueIn, Context output)
				throws IOException, InterruptedException {
			String[] parts = valueIn.toString().split("\t", -1);
			if (parts.length != 2) {
				return;
			}
			String starPair = parts[0];
			int count = Integer.parseInt(parts[1]);
			output.write(new Text(starPair), new IntWritable(count));
		}
	}

	public static class CountCoStarsReducer
			extends Reducer<Text, IntWritable, Text, IntWritable> {

		@Override
		public void reduce(Text key, Iterable<IntWritable> values, Context output)
				throws IOException, InterruptedException {
			int totalCount = 0;
			for (IntWritable value : values) {
				totalCount += value.get();
			}
			output.write(key, new IntWritable(totalCount));
		}
	}

	public static void main(String[] args) throws Exception {
		Configuration conf = new Configuration();
		String[] otherArgs = new GenericOptionsParser(conf, args).getRemainingArgs();
		if (otherArgs.length != 2) {
			System.err.println("Usage: " + CountCoStars.class.getName() + " <in> <out>");
			System.exit(2);
		}

		String inputLocation = otherArgs[0];
		String outputLocation = otherArgs[1];

		Job job = Job.getInstance(new Configuration());

		job.setMapOutputKeyClass(Text.class);
		job.setMapOutputValueClass(IntWritable.class);
		job.setOutputKeyClass(Text.class);
		job.setOutputValueClass(IntWritable.class);

		job.setMapperClass(CountCoStarsMapper.class);
		job.setCombinerClass(CountCoStarsReducer.class);
		job.setReducerClass(CountCoStarsReducer.class);

		FileInputFormat.setInputPaths(job, new Path(inputLocation));
		FileOutputFormat.setOutputPath(job, new Path(outputLocation));

		job.setJarByClass(CountCoStars.class);
		job.waitForCompletion(true);
	}
}
