import java.util.Date;

public class TestMigration {

    public static void oldMethod() {
        System.out.println("Ancienne méthode appelée");
    }

    public static void main(String[] args) {

        // Utilisation d'une ancienne API Date
        Date date = new Date();

        // Appel d'une méthode obsolète
        oldMethod();

        // Affichage
        System.out.println("Date actuelle: " + date);

        // Deuxième appel pour tester remplacement multiple
        oldMethod();
    }
}
