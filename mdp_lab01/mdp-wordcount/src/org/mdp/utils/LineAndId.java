package org.mdp.utils;

import org.mdp.utils.LineAndId;

/**
 * A utility class to store a string and a number.
 * 
 * @author Aidan
 *
 */
public class LineAndId implements Comparable<LineAndId> {
	private final String line;
	private final int id;
	
	public LineAndId(String str, int num){
		this.line = str;
		this.id = num;
	}
	
	@Override
	public int compareTo(LineAndId swm) {
		int comp = line.compareTo(swm.line);
		
		if(comp!=0)
			return comp;
		
		return id - swm.id;
	}
	
	public boolean equals(Object o){
		if(o==null) return false;
		
		if(o==this) return true;
		
		if(!(o instanceof LineAndId)) return false;
		
		LineAndId swn = (LineAndId)o;
		
		return line.equals(swn.line) && id == swn.id;
	}
	
	public int hashCode(){
		return line.hashCode() + id;
	}
	
	public String getString() {
		return line;
	}

	public int getNumber() {
		return id;
	}
}
