package org.mdp.im;

import java.rmi.RemoteException;

import org.mdp.dir.User;

public class InstantMessagingServer implements InstantMessagingStub {

	// default key we will all use for the registry
	public static String DEFAULT_KEY = "Mensaje";
	
	/**
	 * 
	 */
	private static final long serialVersionUID = -6682365848634470441L;

	public long message(User from, String msg) throws RemoteException {
		//TODO here you need to implement the messaging server

		System.out.println("Mensaje recibido de " + from.getUsername() + " (" + from.getRealname() + "): " + msg);
		// return the current time (a long timestamp when the message was received)
		return System.currentTimeMillis();
	}
}
