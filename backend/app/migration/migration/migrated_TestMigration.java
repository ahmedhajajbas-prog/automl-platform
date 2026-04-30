import java.time.LocalDate;

public class TestMigration {

    public static void newMethod() {
        System.out.println("Ancienne méthode appelée");
    }

    public static void main(String[] args) {

        // Utilisation d'une ancienne API Date
        Date date = LocalDate.now();

        // Appel d'une méthode obsolète
        newMethod();

        // Affichage
        System.out.println("Date actuelle: " + date);

        // Deuxième appel pour tester remplacement multiple
        newMethod();
    }
}
