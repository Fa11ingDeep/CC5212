package org.mdp.imdb;

import java.io.BufferedReader;
import java.io.IOException;
import java.util.Iterator;
import java.util.NoSuchElementException;
import java.util.regex.Pattern;

import org.mdp.imdb.ActorMovieParser.MovieRole;
import org.mdp.imdb.MovieRatingParser.MovieRating;

public class MovieRatingParser implements Iterator<MovieRating>{
	// header lines in IMDB
	public static int SKIP_HEADER_LINES = 296;
	
	public static final String YEAR_REGEX = "\\([12][890]\\d{2}\\/?[IVX]*\\)";
	public static final Pattern YEAR_PATTERN = Pattern.compile(YEAR_REGEX);
	
	private final BufferedReader input;
	private MovieRating next = null;
	private int read = 0;
	
	public MovieRatingParser(BufferedReader input) throws IOException{
		this(input, SKIP_HEADER_LINES);
	}
	
	public MovieRatingParser(BufferedReader input, int skip) throws IOException{
		this.input = input;
		while(--skip>=0){
			input.readLine();
		}
		loadNextRating();
	}
	
	public void loadNextRating() throws IOException{
		boolean valid = true;
		String line = null;
		do{
			next = null;
			line = input.readLine();
			if(line==null){
				return;
			}
			read++;
			
			// we expect the first line to be an actor's name with the first movie
			// it should not be empty or start with whitespace
			if(line.isEmpty()){
				System.err.println("Found unexpected empty line at line "+read);
				valid = false;
			}  else if(line.length()<33){
				System.err.println("Found unexpected short line at line "+read+" :: "+line);
				valid = false;
			}
		} while(!valid);
		
		String distr = line.substring(6,16);
		String strVotes = line.substring(17,25).trim();
		String strScore = line.substring(26,31).trim();
		String title = line.substring(32).trim();
		
		int votes = 0;
		float score = 0;
		
		try{
			votes = Integer.parseInt(strVotes);
			score = Float.parseFloat(strScore);
		} catch (Exception e){
			System.err.println("Error parsing scores/vote count from line "+read+" :: "+line);
			loadNextRating();
		}
		
		
		MovieRole mr = ActorMovieParser.parseMovieRole(title);

		
		next = new MovieRating(distr, votes, score, mr);
	}
	
	@Override
	public boolean hasNext() {
		return next!=null;
	}

	public MovieRating next() {
		MovieRating mr = next;
		try {
			loadNextRating();
		} catch (IOException e) {
			e.printStackTrace();
			throw new NoSuchElementException();
		}
		return mr;
	}

	@Override
	public void remove() {
		throw new UnsupportedOperationException();
	}
	
	public static class MovieRating {
		String dist;
		int votes;
		float score;
		MovieRole movie;
		
		public MovieRating(String dist, int votes, float score, MovieRole movie){
			this.dist = dist;
			this.votes = votes;
			this.score = score;
			this.movie = movie;
		}
		
		public String getDistribution(){
			return dist;
		}
		
		public MovieRole getMovie(){
			return movie;
		}
		
		public int getVotes(){
			return votes;
		}
		
		public float getScore(){
			return score;
		}
		
		public String toString(){
			return dist+"\t"+votes+"\t"+score+"\t"+movie;
		}
	}
}
