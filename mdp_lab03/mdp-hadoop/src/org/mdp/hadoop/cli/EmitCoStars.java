package org.mdp.hadoop.cli;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;

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
 * Java class to emit pairs of actresses/actors
 * based on appearing in the same movie
 *
 * The input TSV file contains the following (String[] split = inputLine.split("\t");):
 		 * split[0] is the actor/actress name
		 * split[1] is the movie/tv-series name
		 * split[2] is the year (or -1 if not known)
		 * split[3] is the movie number for movies with the same name/year 
		 * 		e.g., "I", "II" or "null" if not given
		 * split[4] is the movie type; (see enum ActorMovieParser.MovieRole.MovieType) one of: 
		 * 		{ THEATRICAL_MOVIE, TV_SERIES, TV_MINI_SERIES, TV_MOVIE, VIDEO_MOVIE }
		 * split[5] is episode name (only for TV series)
		 * split[6] is for billing (number of appearance in credit or -1 if not given)
		 * split[7] is the role (e.g., character name ... "Michael Corleone")
		 * split[8] is the gender of the actor/actress
 * @author Aidan
 */
public class EmitCoStars {
	
	public static String THEATRICAL_MOVIE = "movie";
	
	/**
	 * This is the Mapper Class. This sends key-value pairs to different machines
	 * based on the key.
	 * 
	 * Remember that the generic is Mapper<InputKey, InputValue, MapKey, MapValue>
	 * 
	 * InputKey we don't care about (a LongWritable will be passed as the input
	 * file offset, but we don't care; we can also set as Object)
	 * 
	 * InputKey will be Text: a line of the file
	 * 
	 * MapKey will be Text: the movie name
	 * 
	 * MapValue will be Text: the actor name
	 * 
	 * @author Aidan
	 *
	 */
	public static class EmitCoStarsMapper extends Mapper<Object, Text, Text, Text>{

		/**
		 * @throws InterruptedException 
		 * 
		 */
		@Override
		public void map(Object keyIn, Text valueIn,
				Context output)
						throws IOException, InterruptedException {
			//TODO implement the map
			String[] split = valueIn.toString().split("\t", -1);
			
			if(split.length < 4) {
				return;
			}
			String movieType = split[3];
			if( THEATRICAL_MOVIE.equals(movieType)) {
				String starName = split[0];
				String movieName = split[1];
				String year = split[2];
				if (starName.isEmpty() || movieName.isEmpty() || year.isEmpty()) {
					return;
				}
				output.write(new Text(movieName + "##" + year), new Text(starName));
			}
		}
	}

	/**
	 * This is the Reducer Class.
	 * 
	 * This collects sets of key-value pairs with the same key on one machine. 
	 * 
	 * Remember that the generic is Reducer<MapKey, MapValue, OutputKey, OutputValue>
	 * 
	 * MapKey will be Text: the movie name
	 * 
	 * MapValue will be Text: the actor name
	 * 
	 * OutputKey will be Text: an actor pairing
	 * 
	 * OutputValue will be IntWritable: the initial count
	 * 
	 * @author Aidan
	 *
	 */
	public static class EmitCoStarsReducer extends 
	     Reducer<Text, Text, Text, IntWritable> {

		/**
		 * @throws InterruptedException 
		 * 
		 */
		@Override
		public void reduce(Text key, Iterable<Text> values,
				Context output) throws IOException, InterruptedException {
			//TODO implement the reduce
			ArrayList<String> stars = new ArrayList<>();
			for (Text value : values) {
				stars.add(value.toString());
			}
			sortAndDeduplicate(stars);
			for (int i = 0; i < stars.size(); i++) {
				for (int j = i + 1; j < stars.size(); j++) {
					String starPair = stars.get(i) + "##" + stars.get(j);
					output.write(new Text(starPair), new IntWritable(1));
				}
			}
		}

		private static void sortAndDeduplicate(ArrayList<String> list) {
			Collections.sort(list);
			for(int i=0; i<list.size()-1; i++) {
				if(list.get(i).equals(list.get(i+1))) {
					list.remove(i+1);
					i--;
				}
			}
		}
	}

	/**
	 * Main method that sets up and runs the job
	 * 
	 * @param args First argument is input, second is output
	 * @throws Exception
	 */
	public static void main(String[] args) throws Exception {
		Configuration conf = new Configuration();
		String[] otherArgs = new GenericOptionsParser(conf, args).getRemainingArgs();
		if (otherArgs.length != 2) {
			System.err.println("Usage: "+EmitCoStars.class.getName()+" <in> <out>");
			System.exit(2);
		}
		String inputLocation = otherArgs[0];
		String outputLocation = otherArgs[1];
		
		Job job = Job.getInstance(new Configuration());
		
		//TODO set:
		// (1) job's map output key class
		// (2) job's map output value class
		// (3) job's (reduce) output key class
		// (4) job's (reduce) output value class
		// (5) job's mapper class
		// (6) job's combiner class (only if applicable)
		// (7) job's reducer class
		
		
		job.setMapOutputKeyClass(Text.class);
		job.setMapOutputValueClass(Text.class);
		job.setOutputKeyClass(Text.class);
		job.setOutputValueClass(IntWritable.class);
		job.setMapperClass(EmitCoStarsMapper.class);
		job.setReducerClass(EmitCoStarsReducer.class);

		FileInputFormat.setInputPaths(job, new Path(inputLocation));
		FileOutputFormat.setOutputPath(job, new Path(outputLocation));
		
		job.setJarByClass(EmitCoStars.class);
		job.waitForCompletion(true);
	}	
}
