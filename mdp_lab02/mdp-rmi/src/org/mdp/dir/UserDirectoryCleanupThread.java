package org.mdp.dir;

import java.rmi.RemoteException;
import java.rmi.registry.LocateRegistry;
import java.util.Map;

/**
 * This will check for broken connections in the directory
 * and remove them intermittently.
 * 
 * @author Aidan
 *
 */
public class UserDirectoryCleanupThread extends Thread {
	public static long WAIT_TIME_MS = 30 * 1000;
	
	UserDirectoryStub uds;
	public UserDirectoryCleanupThread(UserDirectoryStub uds) {
		this.uds = uds;
	}
	
	public void run(){
		while(true) {
			try {
				Thread.sleep(WAIT_TIME_MS);
				Map<String,User> dir = uds.getDirectory();
				for(Map.Entry<String,User> name2user:dir.entrySet()) {
					try {
						LocateRegistry.getRegistry(name2user.getValue().getHost(), name2user.getValue().getPort());
						// registry.lookup(UserDirectoryServer.DEFAULT_KEY);
					} catch(Exception e) {
						System.out.println("Looks like "+name2user.getKey()+" has wandered off ...");
						uds.removeUserWithName(name2user.getKey());
					}
				}
			} catch(InterruptedException ie) {
				return;
			} catch(RemoteException re) {
				throw new RuntimeException(re);
			}
		}
	}
}
