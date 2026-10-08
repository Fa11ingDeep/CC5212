package org.mdp.dir;

import java.io.Serializable;

/**
 * Store/send details of user in the IM system.
 * 
 * Immutable objects (once created, cannot be changed). 
 * 
 * Must implement serializable since objects need to be
 * transmitted over the wire!
 * 
 * @author Aidan
 *
 */
public class User implements Serializable {
	/**
	 * 
	 */
	private static final long serialVersionUID = 2333232814155348186L;
	
	private final String username;
	private final String host;
	private final String realname;
	private final int port;
	private boolean online = true;
	
	/**
	 * Create a new user
	 * 
	 * @param username - a unique username
	 * @param realname - a real name
	 * @param host - an IP address or hostname
	 * @param port - any free port (1 to 65535, not 80, 21, 8080, 8180, etc.)
	 */
	public User(String username, String realname, String host, int port){
		this.username = username;
		this.realname = realname;
		this.host = host;
		this.port = port;
	}

	public String getUsername() {
		return username;
	}
	
	public String getRealname() {
		return realname;
	}

	public String getHost() {
		return host;
	}

	public int getPort() {
		return port;
	}
	
	public boolean getOnline() {
		return online;
	}
	
	public void setOnline(boolean online) {
		this.online = online;
	}
	
	public String toString(){
		return "Username: '"+username+"'\tReal-name: '"+realname+"'\tPort: '"+port+"'\tHost: '"+host+"'"+"'\tOnline: '"+online+"'";
	}
}
