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
 * Sorts star-pair counts from highest to lowest.
 *
 * Input and output lines have the form:
 * starA##starB[tab]count
 */
public class SortCoStarCounts {

	public static class SortCoStarCountsMapper
			extends Mapper<Object, Text, DescendingIntWritable, Text> {

		@Override
		public void map(Object keyIn, Text valueIn, Context output)
				throws IOException, InterruptedException {
			String[] parts = valueIn.toString().split("\t", -1);
			if (parts.length != 2) {
				return;
			}
			String starPair = parts[0];
			int count = Integer.parseInt(parts[1]);
			output.write(new DescendingIntWritable(count), new Text(starPair));
		}
	}

	public static class SortCoStarCountsReducer
			extends Reducer<DescendingIntWritable, Text, Text, IntWritable> {

		@Override
		public void reduce(DescendingIntWritable key, Iterable<Text> values,
				Context output) throws IOException, InterruptedException {
			for (Text starPair : values) {
				output.write(starPair, new IntWritable(key.get()));
			}
		}
	}

	/** Reverses IntWritable's natural order. */
	public static class DescendingIntWritable extends IntWritable {
		public DescendingIntWritable() {
		}

		public DescendingIntWritable(int value) {
			super(value);
		}

		@Override
		public int compareTo(IntWritable other) {
			return -super.compareTo(other);
		}
	}

	public static void main(String[] args) throws Exception {
		Configuration conf = new Configuration();
		String[] otherArgs = new GenericOptionsParser(conf, args).getRemainingArgs();
		if (otherArgs.length != 2) {
			System.err.println("Usage: " + SortCoStarCounts.class.getName() + " <in> <out>");
			System.exit(2);
		}

		String inputLocation = otherArgs[0];
		String outputLocation = otherArgs[1];

		Job job = Job.getInstance(new Configuration());

		job.setMapOutputKeyClass(DescendingIntWritable.class);
		job.setMapOutputValueClass(Text.class);
		job.setOutputKeyClass(Text.class);
		job.setOutputValueClass(IntWritable.class);

		job.setMapperClass(SortCoStarCountsMapper.class);
		job.setReducerClass(SortCoStarCountsReducer.class);
		job.setNumReduceTasks(1);

		FileInputFormat.setInputPaths(job, new Path(inputLocation));
		FileOutputFormat.setOutputPath(job, new Path(outputLocation));

		job.setJarByClass(SortCoStarCounts.class);
		job.waitForCompletion(true);
	}
}
