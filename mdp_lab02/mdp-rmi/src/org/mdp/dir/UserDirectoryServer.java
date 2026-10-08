package org.mdp.dir;

import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.mdp.im.InstantMessagingServer;

/**
 * This is the implementation of UserDirectoryStub.
 * 
 * The stub will be registered in the RMI registry of the server.
 * 
 * When a client calls a method on the stub, the following implementation
 * will be executed on the server.
 * 
 * The main method StartRegistryAndServer can be used to start a server
 * registry and stub on the command line.
 * 
 * @author Aidan
 *
 */
public class UserDirectoryServer implements UserDirectoryStub {
	
	// if true, will check and remove broken connections
	// from the user directory
	public static boolean KEEP_CLEAN = true;

	public static String DEFAULT_KEY = UserDirectoryServer.class.getSimpleName();
	
	/**
	 * 
	 */
	private static final long serialVersionUID = -6025896167995177840L;
	private Map<String,User> directory;
	
	private UserDirectoryCleanupThread cleanup;
	
	public UserDirectoryServer(){
		directory = new ConcurrentHashMap<String,User>();
		
		if(KEEP_CLEAN) {
			cleanup = new UserDirectoryCleanupThread(this);
			cleanup.start();
		}
	}

	/**
	 * Return true if successful, false otherwise.
	 * Will override existing user!
	 */
	public boolean createUser(User u) {
		if(KEEP_CLEAN) {
			if(!checkConnection(u.getHost(),u.getPort())) {
				System.out.println("Cannot connect to user "+u.getUsername()+" at host "+u.getHost()+" port "+u.getPort()+"; not adding ...\n\t"+u);
				return false;
			}
		}
		
		if(u.getUsername()==null)
			return false;
		
		directory.put(u.getUsername(), u);
		
		System.out.println("New user registered; welcome to ...\n\t"+u);
		return true;
	}

	/**
	 * Returns the current directory of users.
	 */
	public Map<String, User> getDirectory() {
		return directory;
	}

	/**
	 * Just an option to clean up if necessary!
	 */
	public User removeUserWithName(String un) {
		System.out.println("Removing username '"+un+"'. Chao!");
		return directory.remove(un);
	}
	
	/**
	 * Will check the connection
	 * @param hostname
	 * @param port
	 * @return
	 */
	public static boolean checkConnection(String hostname, int port) {
		try {
//			LocateRegistry.getRegistry(hostname, port);
			Registry registry = LocateRegistry.getRegistry(hostname, port);
			registry.lookup(InstantMessagingServer.DEFAULT_KEY);
		} catch(Exception e) {
			return false;
		}
		return true;
	}
}
